import importlib.util
import os
import re
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[2] / "DownKit-Android/app/src/main/python/parallel_http.py"
spec = importlib.util.spec_from_file_location("parallel_http", MODULE)
parallel_http = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parallel_http)


class FakeResponse:
    def __init__(self, body, start, end, total):
        self.body = body
        self.offset = 0
        self.status = 206
        self.headers = {
            "Content-Range": f"bytes {start}-{end}/{total}",
            "Content-Length": str(len(body)),
        }

    def read(self, size=-1):
        if size < 0:
            size = len(self.body) - self.offset
        block = self.body[self.offset:self.offset + size]
        self.offset += len(block)
        return block

    def close(self):
        pass


class FakeYDL:
    def __init__(self, data):
        self.data = data
        self.ranges = []

    def urlopen(self, request):
        match = re.fullmatch(r"bytes=(\d+)-(\d+)", request.headers["Range"])
        start, end = map(int, match.groups())
        self.ranges.append((start, end))
        return FakeResponse(self.data[start:end + 1], start, end, len(self.data))


class FakeDownloader:
    def __init__(self, data):
        self.params = {"parallel_download_threads": 8}
        self.ydl = FakeYDL(data)
        self.events = []

    def temp_name(self, filename):
        return filename + ".part"

    def _get_impersonate_target(self, info):
        return None

    def report_destination(self, filename):
        pass

    def to_screen(self, *args, **kwargs):
        pass

    def _hook_progress(self, status, info):
        self.events.append(dict(status))

    def try_rename(self, source, destination):
        os.replace(source, destination)
        # yt-dlp FileDownloader.try_rename returns None after a successful os.replace.

    def try_utime(self, *args):
        return 0


class ParallelHttpTests(unittest.TestCase):
    def test_ranges_are_contiguous_non_overlapping_and_complete(self):
        for total_size in (1, 2, 3, 10, 1024 * 1024 + 31, 100_000_003):
            for workers in (1, 2, 4, 100, 500):
                ranges = parallel_http.split_byte_ranges(total_size, workers)
                self.assertEqual(ranges[0][0], 0)
                self.assertEqual(ranges[-1][1], total_size - 1)
                self.assertLessEqual(len(ranges), 100)
                self.assertEqual(sum(end - start + 1 for start, end in ranges), total_size)
                for left, right in zip(ranges, ranges[1:]):
                    self.assertEqual(left[1] + 1, right[0])

    def test_parallel_download_reassembles_exact_original_bytes(self):
        for size in (2, 3, 1024 * 1024 + 17, 8 * 1024 * 1024 + 9):
            source_bytes = bytes((index * 37) % 256 for index in range(size))
            with tempfile.TemporaryDirectory() as directory:
                destination = str(Path(directory) / "media.bin")
                downloader = FakeDownloader(source_bytes)
                result = parallel_http.parallel_download(
                    downloader,
                    destination,
                    {"url": "https://media.invalid/file", "http_headers": {}},
                    8,
                )
                self.assertTrue(result)
                self.assertEqual(Path(destination).read_bytes(), source_bytes)
                self.assertEqual(downloader.ydl.ranges[0], (0, 0))
                self.assertEqual(downloader.events[-1]["status"], "finished")


if __name__ == "__main__":
    unittest.main()
