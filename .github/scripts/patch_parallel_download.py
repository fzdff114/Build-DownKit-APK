#!/usr/bin/env python3
"""Add user-controlled, overlap-free parallel media downloads to DownKit 1.1.4."""
from pathlib import Path

root = Path(__file__).resolve().parents[2] / "DownKit-Android"
main_path = root / "app/src/main/java/com/downkit/android/MainActivity.kt"
store_path = root / "app/src/main/java/com/downkit/android/DownloadTaskStore.kt"
service_path = root / "app/src/main/java/com/downkit/android/DownloadService.kt"
bridge_path = root / "app/src/main/python/bridge.py"


def replace_once(source: str, old: str, new: str, name: str) -> str:
    if old not in source:
        if new in source:
            return source
        raise SystemExit("Missing expected source block: " + name)
    return source.replace(old, new, 1)


store = store_path.read_text(encoding="utf-8")
store = replace_once(
    store,
    '''    @Synchronized
    fun cookiesPath(context: Context): String = context.getFileStreamPath("cookies.txt").takeIf { it.exists() }?.absolutePath ?: ""''',
    '''    @Synchronized
    fun downloadThreads(context: Context): Int = context.getSharedPreferences("downkit_settings", Context.MODE_PRIVATE)
        .getInt("downloadThreads", 1).coerceIn(1, 100)

    @Synchronized
    fun setDownloadThreads(context: Context, value: Int) {
        context.getSharedPreferences("downkit_settings", Context.MODE_PRIVATE).edit()
            .putInt("downloadThreads", value.coerceIn(1, 100)).apply()
    }

    @Synchronized
    fun cookiesPath(context: Context): String = context.getFileStreamPath("cookies.txt").takeIf { it.exists() }?.absolutePath ?: ""''',
    "download thread preference",
)
store_path.write_text(store, encoding="utf-8")

main = main_path.read_text(encoding="utf-8")
main = replace_once(
    main,
    '''        network.addView(playlistSwitch)
        network.addView(MaterialButton(this).apply {''',
    '''        network.addView(playlistSwitch)
        val threadCountLabel = text("下载并发数：" + DownloadTaskStore.downloadThreads(this@MainActivity), 12, true, Color.rgb(75, 91, 118))
        network.addView(threadCountLabel, margin(top = 9, bottom = 2))
        network.addView(text("范围 1–100。1 为单连接；较高数值会把原始媒体切成互不重叠的区间并发下载，完成后按顺序合并。网站不支持分段请求时会自动回退。", 10, false, Color.rgb(122, 132, 150)), margin(bottom = 3))
        val threadCountSeek = SeekBar(this).apply {
            max = 99
            progress = DownloadTaskStore.downloadThreads(this@MainActivity) - 1
            setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
                override fun onProgressChanged(seekBar: SeekBar?, progress: Int, fromUser: Boolean) {
                    val value = (progress + 1).coerceIn(1, 100)
                    threadCountLabel.text = "下载并发数：$value"
                    if (fromUser) DownloadTaskStore.setDownloadThreads(this@MainActivity, value)
                }
                override fun onStartTrackingTouch(seekBar: SeekBar?) = Unit
                override fun onStopTrackingTouch(seekBar: SeekBar?) = Unit
            })
        }
        network.addView(threadCountSeek, LinearLayout.LayoutParams(-1, dp(42)).apply { bottomMargin = dp(4) })
        network.addView(MaterialButton(this).apply {''',
    "parallel download setting control",
)
main_path.write_text(main, encoding="utf-8")

service = service_path.read_text(encoding="utf-8")
service = replace_once(
    service,
    '''                        "download_video", task.url, task.formatSelector, taskDir.absolutePath,
                        task.id, cookies, proxy, playlist
                    ).toString()''',
    '''                        "download_video", task.url, task.formatSelector, taskDir.absolutePath,
                        task.id, cookies, proxy, playlist, DownloadTaskStore.downloadThreads(this)
                    ).toString()''',
    "download service thread parameter",
)
service_path.write_text(service, encoding="utf-8")

bridge = bridge_path.read_text(encoding="utf-8")
bridge = replace_once(
    bridge,
    '''from yt_dlp import YoutubeDL, version
from yt_dlp.utils import DownloadCancelled, DownloadError''',
    '''from yt_dlp import YoutubeDL, version
from yt_dlp.utils import DownloadCancelled, DownloadError
import parallel_http''',
    "parallel HTTP helper import",
)
bridge = replace_once(
    bridge,
    '''_ACTIVE_TASK_ID = ""


def configure(qjs_path: str = ""):
    global _QJS_PATH
    _QJS_PATH = qjs_path or ""
    _install_android_ffmpeg_merger()''',
    '''_ACTIVE_TASK_ID = ""


def _parallel_download_cancelled():
    if not _ACTIVE_TASK_ID:
        return False
    try:
        return bool(_java_events().isCancelled(str(_ACTIVE_TASK_ID)))
    except Exception:
        return False


def configure(qjs_path: str = ""):
    global _QJS_PATH
    _QJS_PATH = qjs_path or ""
    _install_android_ffmpeg_merger()
    parallel_http.install(_parallel_download_cancelled)''',
    "install parallel HTTP downloader",
)
bridge = replace_once(
    bridge,
    '''def download_video(url: str, format_selector: str, output_dir: str, task_id: str,
                   cookies_path: str = "", proxy: str = "", playlist: bool = False) -> str:''',
    '''def download_video(url: str, format_selector: str, output_dir: str, task_id: str,
                   cookies_path: str = "", proxy: str = "", playlist: bool = False,
                   download_threads: int = 1) -> str:''',
    "download function signature",
)
bridge = replace_once(
    bridge,
    '''    global _ACTIVE_TASK_ID
    _ACTIVE_TASK_ID = str(task_id)
    try:
        url = _valid_url(url)
        _install_android_ffmpeg_merger()''',
    '''    global _ACTIVE_TASK_ID
    _ACTIVE_TASK_ID = str(task_id)
    download_threads = max(1, min(100, int(download_threads or 1)))
    try:
        url = _valid_url(url)
        _install_android_ffmpeg_merger()
        parallel_http.install(_parallel_download_cancelled)''',
    "download thread count and helper registration",
)
bridge = replace_once(
    bridge,
    '''            if fragment_index is not None and fragment_count is not None:
                fragment_text = f"分片 {fragment_index}/{fragment_count}"
            elif fragment_index is not None:
                fragment_text = f"分片 {fragment_index} · 总片数未知"
            else:
                fragment_text = "网站未提供分片信息"''',
    '''            if status.get("parallel_segments"):
                fragment_text = f"HTTP 分段 {status.get('parallel_completed', 0)}/{status.get('parallel_segments')} · 并发 {status.get('parallel_threads', 1)} 路"
            elif fragment_index is not None and fragment_count is not None:
                fragment_text = f"分片 {fragment_index}/{fragment_count}"
            elif fragment_index is not None:
                fragment_text = f"分片 {fragment_index} · 总片数未知"
            else:
                fragment_text = "网站未提供分片信息"''',
    "parallel range progress label",
)
bridge = replace_once(
    bridge,
    '''            "concurrent_fragment_downloads": 4,''',
    '''            "concurrent_fragment_downloads": download_threads,
            "parallel_download_threads": download_threads,''',
    "use configured concurrency for fragments and HTTP ranges",
)
bridge_path.write_text(bridge, encoding="utf-8")

print("DownKit parallel download setting and bridge wiring applied")
