#!/usr/bin/env python3
from pathlib import Path
root = Path(__file__).resolve().parents[2] / "DownKit-Android"
main_path = root / "app/src/main/java/com/downkit/android/MainActivity.kt"
service_path = root / "app/src/main/java/com/downkit/android/DownloadService.kt"
gradle_path = root / "app/build.gradle.kts"
main = main_path.read_text(encoding="utf-8")
service = service_path.read_text(encoding="utf-8")
gradle = gradle_path.read_text(encoding="utf-8")
if 'versionName = "1.1.2"' not in gradle or "versionCode = 7" not in gradle: raise SystemExit("Expected DownKit 1.1.2/versionCode 7 baseline")
gradle = gradle.replace("versionCode = 7", "versionCode = 8", 1).replace('versionName = "1.1.2"', 'versionName = "1.1.3"', 1)
old = """        formats = mutableListOf(
            FormatChoice("自动最佳画质\\n视频 + 音频", "bestvideo+bestaudio/best", "video"),
            FormatChoice("最佳单文件\\n兼容优先", "best", "video"),
            FormatChoice("仅音频\\n最佳可用音质", "bestaudio/best", "audio")
        ) + (0 until result.optJSONArray("formats")?.length().orZero()).mapNotNull { index ->
            val o = result.optJSONArray("formats")?.optJSONObject(index) ?: return@mapNotNull null
            FormatChoice(o.optString("label"), o.optString("selector"), o.optString("kind", "video"))
        }"""
new = """        val parsedFormats = (0 until result.optJSONArray("formats")?.length().orZero()).mapNotNull { index ->
            result.optJSONArray("formats")?.optJSONObject(index)
        }
        fun firstExt(kind: String): String {
            val item = parsedFormats.firstOrNull {
                val k = it.optString("kind", if (it.optString("vcodec") == "none") "audio" else "video")
                k == kind && it.optString("ext").isNotBlank()
            }
            return item?.optString("ext")?.uppercase() ?: "实际格式"
        }
        val videoExt = firstExt("video")
        val audioExt = firstExt("audio")
        formats = listOf(
            FormatChoice("下载视频\\n.$videoExt", "bestvideo+bestaudio/best", "video"),
            FormatChoice("下载音频\\n.$audioExt", "bestaudio/best", "audio")
        )"""
if old not in main: raise SystemExit("Missing parsed-format block")
main = main.replace(old, new, 1)
main = main.replace("        val hasMore = formats.size > 6\n        formatExpandButton?.visibility = if (hasMore) View.VISIBLE else View.GONE\n        formatExpandButton?.text = if (showAllFormats) ", "        formatExpandButton?.visibility = View.GONE\n        downloadButton?.visibility = View.GONE\n        formatExpandButton?.text = if (false) ", 1)
main = main.replace("""                setOnClickListener {
                    selectedFormatIndex = index
                    renderFormatOptions()
                }""", """                setOnClickListener {
                    selectedFormatIndex = index
                    startDownload()
                }""", 1)
if "private var currentTab = 1" not in main: raise SystemExit("Missing currentTab field")
main = main.replace("private var currentTab = 1", "private var currentTab = 1\n    private var restoringTab = false", 1)
if 'currentTab = savedInstanceState?.getInt("downkit.current.tab", 1) ?: 1' not in main:
    anchor = "        autoButtonColorEnabled = DownloadTaskStore.autoButtonColor(this)"
    if anchor not in main: raise SystemExit("Missing onCreate state anchor")
    main = main.replace(anchor, '        currentTab = savedInstanceState?.getInt("downkit.current.tab", 1) ?: 1\n' + anchor, 1)
pos = main.find("renderHome()")
if pos < 0: raise SystemExit("Missing initial renderHome call")
main = main[:pos] + """when (currentTab) {
            2 -> renderTasks()
            3 -> renderSettings()
            else -> renderHome()
        }""" + main[pos + len("renderHome()"): ]
if 'outState.putInt("downkit.current.tab", currentTab)' not in main:
    anchor = '        outState.putString("downkit.input.url", urlField?.text?.toString()?.trim().orEmpty().ifBlank { savedInputUrl })'
    if anchor not in main: raise SystemExit("Missing onSaveInstanceState anchor")
    main = main.replace(anchor, '        outState.putInt("downkit.current.tab", currentTab)\n' + anchor, 1)
start = main.find("        val autoAccentSwitch = SwitchCompat(this).apply")
if start >= 0:
    end = main.find('        appearance.addView(text("开启后会提取当前背景的主要颜色', start)
    if end < 0: raise SystemExit("Missing auto color help anchor")
    main = main[:start] + "        if (DownloadTaskStore.backgroundUri(this).isNotBlank()) {\n" + main[start:end] + "        }\n" + main[end:]
preview_start = main.find("        appearance.addView(MaterialButton(this).apply {", main.find("打开 RGB 调色功能"))
if preview_start >= 0:
    preview_text = main.find('text = "按钮颜色预览"', preview_start)
    if preview_text >= 0:
        preview_end = main.find("        val rgbLabels = mutableListOf<TextView>()", preview_text)
        if preview_end < 0: raise SystemExit("Missing RGB label anchor")
        main = main[:preview_start] + main[preview_end:]
service = service.replace("private fun buildNotification(title: String, progress: Int, status: String): Notification {", """private fun buildNotification(title: String, progress: Int, status: String): Notification {
        val task = DownloadTaskStore.all(this).firstOrNull { it.title == title && it.status == status }
        val media = task?.mediaInfo?.takeIf { it.isNotBlank() } ?: task?.formatLabel.orEmpty()
        val bytes = task?.let { File(filesDir, "downloads/" + it.id).walkTopDown().filter { f -> f.isFile }.sumOf { f -> f.length() } } ?: 0L
        val size = when {
            bytes >= 1024L * 1024L * 1024L -> String.format("%.1f GB", bytes / 1073741824.0)
            bytes >= 1024L * 1024L -> String.format("%.1f MB", bytes / 1048576.0)
            bytes >= 1024L -> String.format("%.0f KB", bytes / 1024.0)
            bytes > 0 -> "$bytes B"
            else -> "大小未知"
        }
        val compact = listOf(media, size, status).filter { it.isNotBlank() }.joinToString(" · ")
""", 1)
service = service.replace('.setContentText(if (progress in 1..99) "$progress%" else status)', '.setContentText(if (progress in 1..99) "$progress% · $compact" else compact)', 2)
gradle_path.write_text(gradle, encoding="utf-8")
main_path.write_text(main, encoding="utf-8")
service_path.write_text(service, encoding="utf-8")
print("DownKit 1.1.3 patch applied")
