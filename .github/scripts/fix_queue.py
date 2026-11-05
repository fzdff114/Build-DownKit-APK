#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")

def replace_once(text: str, old: str, new: str, name: str) -> str:
    if old not in text:
        raise SystemExit(f"Missing patch anchor: {name}")
    return text.replace(old, new, 1)

# MainActivity: bind metadata and formats to the exact URL inspected.
main_path = root / "app/src/main/java/com/downkit/android/MainActivity.kt"
main = main_path.read_text()

main = replace_once(
    main,
    "    private var parsedInfo: JSONObject? = null",
    "    private var parsedInfo: JSONObject? = null\n    private var parsedUrl: String? = null\n    private var parseGeneration: Long = 0L",
    "parsed URL state fields",
)
main = replace_once(
    main,
    "    private fun renderHome() {\n        currentTab = 1",
    "    private fun renderHome() {\n        currentTab = 1\n        parseGeneration += 1\n        parsedInfo = null\n        parsedUrl = null\n        formats = emptyList()",
    "reset home parse state",
)

watcher = """        urlField?.addTextChangedListener(object : android.text.TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) = Unit
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) = Unit
            override fun afterTextChanged(s: android.text.Editable?) {
                parseGeneration += 1
                parsedInfo = null
                parsedUrl = null
                formats = emptyList()
                downloadButton?.isEnabled = false
                parseButton?.isEnabled = true
                parseButton?.text = "解析链接"
                infoCard?.visibility = View.GONE
            }
        })
        linkLayout.addView(urlField)"""
main = replace_once(
    main,
    "        linkLayout.addView(urlField)",
    watcher,
    "invalidate parsed metadata whenever URL changes",
)

parse_start = main.index("    private fun parseLink()")
parse_end = main.index("    private fun startDownload()", parse_start)
parse_block = main[parse_start:parse_end]
parse_block = replace_once(
    parse_block,
    """        val url = urlField?.text?.toString()?.trim().orEmpty()
        if (!(url.startsWith("https://") || url.startsWith("http://"))) {
            toast("请先粘贴完整的视频链接")
            return
        }
        parsedInfo = null""",
    """        val url = urlField?.text?.toString()?.trim().orEmpty()
        val parsedUri = runCatching { Uri.parse(url) }.getOrNull()
        if (!(url.startsWith("https://") || url.startsWith("http://")) || parsedUri?.host.isNullOrBlank()) {
            toast("请先粘贴完整的视频链接")
            return
        }
        val requestGeneration = ++parseGeneration
        parsedInfo = null
        parsedUrl = null""",
    "validate URL and capture parse generation",
)
parse_block = replace_once(
    parse_block,
    '''            runOnUiThread {
                parseButton?.isEnabled = true
                parseButton?.text = "解析链接"''',
    '''            runOnUiThread {
                if (requestGeneration != parseGeneration || urlField?.text?.toString()?.trim() != url) return@runOnUiThread
                parseButton?.isEnabled = true
                parseButton?.text = "解析链接"''',
    "ignore stale asynchronous parse results",
)
parse_block = replace_once(
    parse_block,
    """                parsedInfo = result
                val views = infoCard?.tag as? HomeViews""",
    """                parsedInfo = result
                parsedUrl = url
                val views = infoCard?.tag as? HomeViews""",
    "store URL alongside parsed metadata",
)
main = main[:parse_start] + parse_block + main[parse_end:]

start = main.index("    private fun startDownload()")
end = main.index("    private fun renderTasks()", start)
download = main[start:end]
download = replace_once(
    download,
    """        val info = parsedInfo ?: return toast("请先解析链接")
        val choice""",
    """        val info = parsedInfo ?: return toast("请先解析当前链接")
        val url = parsedUrl?.takeIf { it.isNotBlank() }
            ?: return toast("链接已变化或未保存，请重新解析")
        if (urlField?.text?.toString()?.trim() != url) {
            parsedInfo = null
            parsedUrl = null
            downloadButton?.isEnabled = false
            return toast("链接已变化，请重新解析后再下载")
        }
        val choice""",
    "use immutable parsed URL snapshot",
)
download = replace_once(
    download,
    "            urlField?.text?.toString()?.trim().orEmpty(),",
    "            url,",
    "do not reread editable URL when queueing",
)
main = main[:start] + download + main[end:]

main = replace_once(
    main,
    '            body.addView(text(task.title, 15, true, Color.rgb(23, 32, 51)).apply { maxLines = 2 }, margin(bottom = 5))',
    '            body.addView(text(task.title, 15, true, Color.rgb(23, 32, 51)).apply { maxLines = 2 }, margin(bottom = 4))\n            body.addView(text(task.url, 11, false, Color.rgb(122, 132, 150)).apply { maxLines = 1; ellipsize = android.text.TextUtils.TruncateAt.END }, margin(bottom = 7))',
    "display saved source URL on each task card",
)
main_path.write_text(main)

# DownloadTaskStore: reject blank/invalid links and durably write new queue entries.
store_path = root / "app/src/main/java/com/downkit/android/DownloadTaskStore.kt"
store = store_path.read_text()
store = replace_once(
    store,
    "import android.content.Context",
    "import android.content.Context\nimport android.net.Uri",
    "URI validation import",
)
store = replace_once(
    store,
    "    private fun write(context: Context, tasks: List<DownloadTask>) {",
    "    private fun write(context: Context, tasks: List<DownloadTask>, persistImmediately: Boolean = false) {",
    "durable write option",
)
store = replace_once(
    store,
    "        context.getSharedPreferences(FILE, Context.MODE_PRIVATE).edit().putString(KEY, array.toString()).apply()",
    """        val editor = context.getSharedPreferences(FILE, Context.MODE_PRIVATE).edit().putString(KEY, array.toString())
        if (persistImmediately) {
            check(editor.commit()) { "下载任务没有成功写入本机队列，请重试" }
        } else {
            editor.apply()
        }""",
    "commit newly enqueued task before service starts",
)
store = replace_once(
    store,
    """    fun add(context: Context, url: String, title: String, formatSelector: String, formatLabel: String): DownloadTask {
        val task = DownloadTask(UUID.randomUUID().toString(), url, title, formatSelector, formatLabel)
        val tasks = read(context)
        tasks.add(0, task)
        write(context, tasks.take(100))
        return task
    }""",
    """    fun add(context: Context, url: String, title: String, formatSelector: String, formatLabel: String): DownloadTask {
        val cleanUrl = url.trim()
        val parsed = Uri.parse(cleanUrl)
        require((parsed.scheme == "http" || parsed.scheme == "https") && !parsed.host.isNullOrBlank()) {
            "下载链接为空或不完整，请返回首页重新解析"
        }
        val task = DownloadTask(UUID.randomUUID().toString(), cleanUrl, title, formatSelector, formatLabel)
        val tasks = read(context)
        tasks.add(0, task)
        val active = tasks.filterNot { it.status == "已完成" || it.status == "已取消" || it.status == "失败" }
        val finished = tasks.filter { it.status == "已完成" || it.status == "已取消" || it.status == "失败" }.take(150)
        write(context, active + finished, persistImmediately = true)
        return task
    }""",
    "validate and persist multi-task queue item",
)
store_path.write_text(store)

# Upgrade version only from the known 1.0.1 build base.
gradle_path = root / "app/build.gradle.kts"
gradle = gradle_path.read_text()
if "versionCode = 2" not in gradle or 'versionName = "1.0.1"' not in gradle:
    raise SystemExit("Unexpected base app version; expected 1.0.1")
gradle = gradle.replace("versionCode = 2", "versionCode = 3", 1)
gradle = gradle.replace('versionName = "1.0.1"', 'versionName = "1.0.2"', 1)
gradle_path.write_text(gradle)

print("DownKit 1.0.2 URL snapshot and durable queue patch applied.")
