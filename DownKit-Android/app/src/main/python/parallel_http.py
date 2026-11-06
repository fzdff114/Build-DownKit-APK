"""Parallel, non-overlapping HTTP Range downloader for DownKit."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import math
import os
import shutil
import threading
import time


class RangeUnsupported(Exception):
    """Raised when a server does not honor exact HTTP byte ranges."""


def split_byte_ranges(total_size: int, worker_count: int):
    """Return contiguous inclusive ranges covering [0, total_size - 1] exactly once."""
    total_size = int(total_size)
    worker_count = max(1, min(100, int(worker_count)))
    if total_size <= 0:
        return []
    worker_count = min(worker_count, total_size)
    base, remainder = divmod(total_size, worker_count)
    ranges = []
    start = 0
    for index in range(worker_count):
        length = base + (1 if index < remainder else 0)
        end = start + length - 1
        ranges.append((start, end))
        start = end + 1
    return ranges


_CANCEL_CHECK = lambda: False
_INSTALLED = False
_INSTALL_LOCK = threading.Lock()
_MIN_RANGE_BYTES = 1024 * 1024
_BLOCK_SIZE = 256 * 1024


def install(cancel_check=None):
    """Patch yt-dlp HttpFD once; ineligible downloads use upstream HttpFD unchanged."""
    global _CANCEL_CHECK, _INSTALLED
    if cancel_check is not None:
        _CANCEL_CHECK = cancel_check
    if _INSTALLED:
        return
    with _INSTALL_LOCK:
        if _INSTALLED:
            return
        from yt_dlp.downloader.http import HttpFD

        original = HttpFD.real_download

        def downkit_real_download(self, filename, info_dict):
            requested = self.params.get("parallel_download_threads", 1)
            try:
                workers = max(1, min(100, int(requested)))
            except (TypeError, ValueError):
                workers = 1
            if workers <= 1:
                return original(self, filename, info_dict)
            try:
                result = parallel_download(self, filename, info_dict, workers)
            except RangeUnsupported:
                result = None
            if result is None:
                return original(self, filename, info_dict)
            return result

        downkit_real_download._downkit_original = original
        HttpFD.real_download = downkit_real_download
        _INSTALLED = True


def _close(response):
    try:
        response.close()
    except Exception:
        pass


def _eligible(self, filename, info_dict):
    url = str(info_dict.get("url") or "")
    if not url.startswith(("http://", "https://")):
        return False
    if self.params.get("test") or self.params.get("ratelimit"):
        return False
    if info_dict.get("request_data") is not None:
        return False
    # FragmentFD sets frag_resume_len for native HLS/DASH fragments.
    if "frag_resume_len" in info_dict or info_dict.get("ctx_id") is not None:
        return False
    if info_dict.get("downloader_options", {}).get("http_chunk_size"):
        return False
    # Leave yt-dlp's native resume bookkeeping intact for interrupted downloads.
    if os.path.exists(self.temp_name(filename)):
        return False
    return True


def parallel_download(self, filename, info_dict, requested_workers):
    """Download a progressive HTTP resource in exact byte ranges, then join in order.

    Returns True when handled, None when the URL/server is not suitable for Range.
    """
    if not _eligible(self, filename, info_dict):
        return None

    from yt_dlp.networking import Request
    from yt_dlp.utils import DownloadCancelled, parse_http_range
    from yt_dlp.utils.networking import HTTPHeaderDict

    url = info_dict["url"]
    headers = HTTPHeaderDict({"Accept-Encoding": "identity"}, info_dict.get("http_headers"))
    if headers.get("Range"):
        return None

    extensions = {}
    impersonate_target = self._get_impersonate_target(info_dict)
    if impersonate_target is not None:
        extensions["impersonate"] = impersonate_target

    # Keep the probe byte as byte 0 of segment 0; no byte is transferred twice.
    probe_headers = HTTPHeaderDict(headers)
    probe_headers["Range"] = "bytes=0-0"
    probe = None
    try:
        probe = self.ydl.urlopen(Request(url, None, probe_headers, extensions=extensions))
        if getattr(probe, "status", None) != 206 or probe.headers.get("Content-Encoding"):
            return None
        content_range = parse_http_range(probe.headers.get("Content-Range"))
        if not content_range or content_range[0] != 0 or content_range[1] != 0:
            return None
        total_size = content_range[2]
        if total_size is None or int(total_size) < 2:
            return None
        total_size = int(total_size)
        first_byte = probe.read(2)
        if len(first_byte) != 1:
            return None
        last_modified = probe.headers.get("Last-Modified")
    except Exception:
        # A failed range probe must not block an ordinary full GET.
        return None
    finally:
        if probe is not None:
            _close(probe)

    requested_workers = max(2, min(100, int(requested_workers)))
    # Do not issue hundreds of tiny requests for a small media file.
    size_limited_workers = max(2, int(math.ceil(total_size / _MIN_RANGE_BYTES)))
    workers = min(requested_workers, size_limited_workers, total_size)
    if workers < 2:
        return None

    ranges = split_byte_ranges(total_size, workers)
    if len(ranges) < 2:
        return None

    tmpfilename = self.temp_name(filename)
    part_dir = tmpfilename + ".ranges"
    if os.path.exists(part_dir):
        shutil.rmtree(part_dir, ignore_errors=True)
    os.makedirs(part_dir, exist_ok=True)
    part_paths = [os.path.join(part_dir, f"segment-{i:03d}.part") for i in range(len(ranges))]

    counts = [1] + [0] * (len(ranges) - 1)
    completed = [False] * len(ranges)
    progress_lock = threading.Lock()
    started = time.monotonic()
    last_emit = 0.0
    abort_event = threading.Event()

    with open(part_paths[0], "wb") as first_part:
        first_part.write(first_byte)

    def cancelled():
        if abort_event.is_set():
            return True
        try:
            return bool(_CANCEL_CHECK())
        except Exception:
            return False

    def emit(force=False):
        nonlocal last_emit
        now = time.monotonic()
        if not force and now - last_emit < 0.20:
            return
        last_emit = now
        downloaded = sum(counts)
        elapsed = max(0.001, now - started)
        speed = downloaded / elapsed
        eta = int(max(0, total_size - downloaded) / speed) if speed > 0 else None
        self._hook_progress({
            "status": "downloading",
            "downloaded_bytes": downloaded,
            "total_bytes": total_size,
            "speed": speed,
            "eta": eta,
            "filename": filename,
            "parallel_threads": workers,
            "parallel_segments": len(ranges),
            "parallel_completed": sum(1 for item in completed if item),
        }, info_dict)

    def set_count(index, value):
        with progress_lock:
            counts[index] = value
            emit(force=True)

    def download_segment(index, byte_range):
        start, end = byte_range
        segment_path = part_paths[index]
        initial_count = 1 if index == 0 else 0
        request_start = max(start, 1) if index == 0 else start
        expected = max(0, end - request_start + 1)
        last_error = None

        for attempt in range(3):
            if cancelled():
                raise DownloadCancelled()
            set_count(index, initial_count)
            try:
                written = initial_count
                with open(segment_path, "wb") as output:
                    if index == 0:
                        output.write(first_byte)
                    if expected:
                        request_headers = HTTPHeaderDict(headers)
                        request_headers["Range"] = f"bytes={request_start}-{end}"
                        response = self.ydl.urlopen(Request(url, None, request_headers, extensions=extensions))
                        try:
                            if getattr(response, "status", None) != 206 or response.headers.get("Content-Encoding"):
                                raise RangeUnsupported("服务器未按要求返回 HTTP 206 分段内容")
                            actual_range = parse_http_range(response.headers.get("Content-Range"))
                            if not actual_range or actual_range != (request_start, end, total_size):
                                raise RangeUnsupported("服务器返回的 Content-Range 与请求区间不一致")
                            content_length = response.headers.get("Content-Length")
                            if content_length is not None and int(content_length) != expected:
                                raise RangeUnsupported("服务器返回的分段长度不正确")
                            while True:
                                if cancelled():
                                    raise DownloadCancelled()
                                block = response.read(_BLOCK_SIZE)
                                if not block:
                                    break
                                output.write(block)
                                written += len(block)
                                with progress_lock:
                                    counts[index] = written
                                    emit()
                        finally:
                            _close(response)
                if written != end - start + 1 or os.path.getsize(segment_path) != end - start + 1:
                    raise IOError(f"第 {index + 1} 段数据不完整，预期 {end - start + 1} 字节，实际 {written} 字节")
                with progress_lock:
                    counts[index] = written
                    completed[index] = True
                    emit(force=True)
                return index
            except (RangeUnsupported, DownloadCancelled):
                raise
            except Exception as exc:
                last_error = exc
                if attempt < 2:
                    time.sleep(0.25 * (attempt + 1))
        raise last_error or IOError("分段下载失败")

    self.report_destination(filename)
    self.to_screen(f"[download] HTTP Range 并发分段：{workers} 路，{total_size} 字节")
    try:
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="DownKitRange") as pool:
            futures = [pool.submit(download_segment, index, byte_range)
                       for index, byte_range in enumerate(ranges)]
            for future in as_completed(futures):
                if cancelled():
                    abort_event.set()
                    for pending in futures:
                        pending.cancel()
                    raise DownloadCancelled()
                try:
                    future.result()
                except Exception:
                    abort_event.set()
                    for pending in futures:
                        pending.cancel()
                    raise

        if not all(completed):
            raise IOError("有分段未完成，拒绝合并不完整文件")
        if cancelled():
            raise DownloadCancelled()

        # Join ascending ranges. Each byte is written once, in the original order.
        with open(tmpfilename, "wb") as output:
            for index, (start, end) in enumerate(ranges):
                if cancelled():
                    raise DownloadCancelled()
                expected = end - start + 1
                if os.path.getsize(part_paths[index]) != expected:
                    raise IOError(f"第 {index + 1} 段长度校验失败，已停止合并")
                with open(part_paths[index], "rb") as source:
                    shutil.copyfileobj(source, output, length=_BLOCK_SIZE)
            output.flush()
            os.fsync(output.fileno())

        actual_size = os.path.getsize(tmpfilename)
        if actual_size != total_size:
            raise IOError(f"合并后文件大小不匹配：预期 {total_size}，实际 {actual_size}")
        if not self.try_rename(tmpfilename, filename):
            raise IOError("无法将完整分段文件移动到目标位置")
        if self.params.get("updatetime") and last_modified:
            info_dict["filetime"] = self.try_utime(filename, last_modified)
        self._hook_progress({
            "downloaded_bytes": total_size,
            "total_bytes": total_size,
            "filename": filename,
            "status": "finished",
            "elapsed": time.monotonic() - started,
            "parallel_threads": workers,
            "parallel_segments": len(ranges),
            "parallel_completed": len(ranges),
        }, info_dict)
        return True
    except Exception:
        try:
            if os.path.exists(tmpfilename):
                os.remove(tmpfilename)
        except OSError:
            pass
        raise
    finally:
        shutil.rmtree(part_dir, ignore_errors=True)
