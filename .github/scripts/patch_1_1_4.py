#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parents[2] / "DownKit-Android"
main_path = root / "app/src/main/java/com/downkit/android/MainActivity.kt"
gradle_path = root / "app/build.gradle.kts"
main = main_path.read_text(encoding="utf-8")
gradle = gradle_path.read_text(encoding="utf-8")

def replace_once(source, old, new, name):
    if old not in source:
        if new in source:
            return source  # Already patched; keep this script idempotent.
        raise SystemExit("Missing expected source block: " + name)
    return source.replace(old, new, 1)

if not ('versionName = "1.1.3"' in gradle or 'versionName = "1.1.4"' in gradle):
    raise SystemExit("Expected a 1.1.3/1.1.4 DownKit source baseline")
if "versionCode = 8" in gradle:
    gradle = gradle.replace("versionCode = 8", "versionCode = 9", 1)
elif "versionCode = 9" not in gradle:
    raise SystemExit("Expected versionCode 8 or 9 baseline")
# Public APK name/version stays 1.1.3; versionCode 9 preserves in-place upgrade from the original 1.1.3/1.1.2 release chain.
gradle = gradle.replace('versionName = "1.1.4"', 'versionName = "1.1.3"', 1)
if 'versionName = "1.1.3"' not in gradle or "versionCode = 9" not in gradle:
    raise SystemExit("Final app version must be 1.1.3 (versionCode 9)")

# Use the system content picker; the crop is copied into private app storage.
main = replace_once(main,
'''    private val backgroundPicker = registerForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) openBackgroundCrop(uri)
    }''',
'''    private val backgroundPicker = registerForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        if (uri != null) openBackgroundCrop(uri)
    }''', "background picker contract")
main = replace_once(main,
'setOnClickListener { backgroundPicker.launch(arrayOf("image/*")) }',
'setOnClickListener { backgroundPicker.launch("image/*") }', "background picker launch")

# A stale preference must not enable or expose auto-accent without a background.
main = replace_once(main,
'''        autoButtonColorEnabled = DownloadTaskStore.autoButtonColor(this)
        buttonAccentColor = if (autoButtonColorEnabled) dominantAccentFromStoredBackground() ?: DownloadTaskStore.buttonColor(this)
            else DownloadTaskStore.buttonColor(this)''',
'''        val hasStoredBackground = DownloadTaskStore.backgroundUri(this).isNotBlank()
        autoButtonColorEnabled = hasStoredBackground && DownloadTaskStore.autoButtonColor(this)
        if (!hasStoredBackground && DownloadTaskStore.autoButtonColor(this)) {
            DownloadTaskStore.setAutoButtonColor(this, false)
        }
        buttonAccentColor = if (autoButtonColorEnabled) dominantAccentFromStoredBackground() ?: DownloadTaskStore.buttonColor(this)
            else DownloadTaskStore.buttonColor(this)''', "auto-accent initialization")

# Replace the two direct-download format tiles with two category buttons.
main = replace_once(main,
'''        infoColumn.addView(text("下载格式 · 双列选择", 13, true, Color.rgb(23, 32, 51)), margin(bottom = 3))
        infoColumn.addView(text("格式列表显示网站实际封装（如 MP4、WebM、MKV、M4A），不会强制转成 MP4。", 10, false, Color.rgb(122, 132, 150)), margin(bottom = 6))
        formatGrid = GridLayout(this).apply { columnCount = 2; alignmentMode = GridLayout.ALIGN_BOUNDS; useDefaultMargins = false }
        formatScroll = null
        infoColumn.addView(formatGrid!!, LinearLayout.LayoutParams(-1, ViewGroup.LayoutParams.WRAP_CONTENT).apply { bottomMargin = dp(7) })
        val moreFormats = MaterialButton(this, null, com.google.android.material.R.attr.materialButtonOutlinedStyle).apply {
            text = "展开更多格式"
            isAllCaps = false
            visibility = View.GONE
            setOnClickListener { showAllFormats = !showAllFormats; renderFormatOptions() }
        }
        formatExpandButton = moreFormats
        infoColumn.addView(moreFormats, margin(bottom = 7))
        downloadButton = MaterialButton(this).apply {
            text = "开始下载"
            isAllCaps = false
            setIconResource(android.R.drawable.stat_sys_download)
            isEnabled = false
            setOnClickListener { startDownload() }
        }
        infoColumn.addView(downloadButton, LinearLayout.LayoutParams(-1, dp(48)))''',
'''        infoColumn.addView(text("下载格式 · 分类选择", 13, true, Color.rgb(23, 32, 51)), margin(bottom = 3))
        infoColumn.addView(text("先选择视频或音频，再从网站实际提供的格式列表中选择清晰度、封装和音质。", 10, false, Color.rgb(122, 132, 150)), margin(bottom = 6))
        formatGrid = GridLayout(this).apply { columnCount = 2; alignmentMode = GridLayout.ALIGN_BOUNDS; useDefaultMargins = false }
        formatScroll = null
        infoColumn.addView(formatGrid!!, LinearLayout.LayoutParams(-1, ViewGroup.LayoutParams.WRAP_CONTENT).apply { bottomMargin = dp(7) })
        downloadButton = MaterialButton(this).apply {
            text = "开始下载"
            isAllCaps = false
            setIconResource(android.R.drawable.stat_sys_download)
            isEnabled = false
            setOnClickListener { startDownload() }
        }
        infoColumn.addView(downloadButton, LinearLayout.LayoutParams(-1, dp(48)))''', "format category UI")

# Retain every parsed yt-dlp format and its actual label/selector/extension.
main = replace_once(main,
'''        val parsedFormats = (0 until result.optJSONArray("formats")?.length().orZero()).mapNotNull { index ->
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
        )
        selectedFormatIndex = selectedFormatIndex.coerceIn(0, (formats.size - 1).coerceAtLeast(0))
        renderFormatOptions()
        parseStageView?.text = "解析完成 · 已读取标题、封面和 ${formats.size} 种格式"''',
'''        val formatArray = result.optJSONArray("formats")
        formats = listOf(
            FormatChoice("自动最佳画质 · 视频 + 音频", "bestvideo+bestaudio/best", "video"),
            FormatChoice("兼容优先 · 最佳单文件", "best", "video"),
            FormatChoice("仅音频 · 最佳可用音质", "bestaudio/best", "audio")
        ) + (0 until (formatArray?.length() ?: 0)).mapNotNull { index ->
            val item = formatArray?.optJSONObject(index) ?: return@mapNotNull null
            val selector = item.optString("selector").takeIf { it.isNotBlank() } ?: return@mapNotNull null
            val kind = item.optString("kind").ifBlank { if (item.optString("has_video") == "true") "video" else "audio" }
            val label = item.optString("label").ifBlank {
                val ext = item.optString("ext").ifBlank { "格式未知" }.uppercase()
                if (kind == "audio") "音频 · $ext" else "视频 · $ext"
            }
            FormatChoice(label, selector, if (kind == "audio") "audio" else "video")
        }
        selectedFormatIndex = 0
        renderFormatOptions()
        downloadButton?.isEnabled = formats.isNotEmpty()
        val videoCount = formats.count { it.kind == "video" }
        val audioCount = formats.count { it.kind == "audio" }
        parseStageView?.text = "解析完成 · 视频格式 ${videoCount} 种 · 音频格式 ${audioCount} 种"''',
"parsed format categories")

start = main.find("    private fun renderFormatOptions() {")
end = main.find("    private fun parseLink()", start)
if start < 0 or end < 0:
    raise SystemExit("Missing format renderer range")
renderer = '''    private fun renderFormatOptions() {
        val grid = formatGrid ?: return
        grid.removeAllViews()
        grid.columnCount = 2
        val videoFormats = formats.filter { it.kind == "video" }
        val audioFormats = formats.filter { it.kind == "audio" }

        fun categoryButton(kind: String, count: Int, title: String) =
            MaterialButton(this, null, com.google.android.material.R.attr.materialButtonOutlinedStyle).apply {
                val selected = formats.getOrNull(selectedFormatIndex)?.takeIf { it.kind == kind }
                text = when {
                    count == 0 -> "$title\\n暂无可用格式"
                    selected != null -> "$title\\n${selected.label}"
                    else -> "$title\\n选择格式（$count 种）"
                }
                isAllCaps = false
                maxLines = 2
                ellipsize = android.text.TextUtils.TruncateAt.END
                textSize = 12f
                minWidth = 0
                minHeight = dp(58)
                insetTop = 0
                insetBottom = 0
                isEnabled = count > 0
                setOnClickListener { showFormatPicker(kind) }
            }

        listOf(
            categoryButton("video", videoFormats.size, "视频选项"),
            categoryButton("audio", audioFormats.size, "音频选项")
        ).forEach { button ->
            val params = GridLayout.LayoutParams(
                GridLayout.spec(GridLayout.UNDEFINED),
                GridLayout.spec(GridLayout.UNDEFINED, 1f)
            ).apply {
                width = 0
                height = dp(62)
                setMargins(dp(3), dp(3), dp(3), dp(3))
            }
            grid.addView(button, params)
        }
        grid.requestLayout()
    }

    private fun showFormatPicker(kind: String) {
        val choices = formats.filter { it.kind == kind }
        if (choices.isEmpty()) {
            toast(if (kind == "audio") "网站没有提供可用的音频格式" else "网站没有提供可用的视频格式")
            return
        }
        val labels = choices.map { it.label }.toTypedArray()
        var checked = choices.indexOfFirst { formats.indexOf(it) == selectedFormatIndex }
            .takeIf { it >= 0 } ?: 0
        val title = if (kind == "audio") "选择音频格式" else "选择视频格式"
        val dialog = androidx.appcompat.app.AlertDialog.Builder(this)
            .setTitle(title)
            .setSingleChoiceItems(labels, checked) { _, which -> checked = which }
            .setNegativeButton("取消", null)
            .setPositiveButton("确定", null)
            .create()
        dialog.setOnShowListener {
            dialog.getButton(androidx.appcompat.app.AlertDialog.BUTTON_POSITIVE).setOnClickListener {
                selectedFormatIndex = formats.indexOf(choices[checked]).coerceAtLeast(0)
                dialog.dismiss()
                renderFormatOptions()
                downloadButton?.isEnabled = true
            }
        }
        dialog.show()
    }

'''
main = main[:start] + renderer + main[end:]

main = replace_once(main,
'''                    val tag = release.optString("tag_name", "").trim()
                    val version = tag.removePrefix("v").removePrefix("V")
                    val assets = release.optJSONArray("assets") ?: org.json.JSONArray()
                    val asset = (0 until assets.length()).mapNotNull { assets.optJSONObject(it) }.firstOrNull {
                        it.optString("name").endsWith(".apk", ignoreCase = true)
                    } ?: throw IllegalStateException("最新发行版没有 APK 安装文件")
                    ReleaseInfo(version, tag, release.optString("html_url", RELEASES_URL), asset.optString("browser_download_url"), asset.optString("digest"), release.optString("body").take(900))''',
'''                    val tag = release.optString("tag_name", "").trim()
                    val notes = release.optString("body")
                    val version = Regex("(?im)^App version:\\\\s*([0-9]+(?:\\\\.[0-9]+){1,3})")
                        .find(notes)?.groupValues?.get(1)
                        ?: tag.removePrefix("v").removePrefix("V")
                    val assets = release.optJSONArray("assets") ?: org.json.JSONArray()
                    val asset = (0 until assets.length()).mapNotNull { assets.optJSONObject(it) }.firstOrNull {
                        it.optString("name").endsWith(".apk", ignoreCase = true)
                    } ?: throw IllegalStateException("最新发行版没有 APK 安装文件")
                    ReleaseInfo(version, tag, release.optString("html_url", RELEASES_URL), asset.optString("browser_download_url"), asset.optString("digest"), notes.take(900))''',
"replacement release version detection")

# Decode the content URI immediately, explain failures, and save the cropped bitmap locally.
main = replace_once(main,
'''                val bitmap = decoded.getOrNull()
                if (bitmap == null) {
                    toast("无法读取图片，请选择其他图片")
                    return@runOnUiThread
                }''',
'''                val bitmap = decoded.getOrNull()
                if (bitmap == null) {
                    val reason = decoded.exceptionOrNull()?.message?.take(100).orEmpty()
                    toast("背景图片导入失败：${reason.ifBlank { "无法读取图片数据" }}")
                    return@runOnUiThread
                }''', "background decode error")
main = replace_once(main,
'''                runCatching {
                    contentResolver.takePersistableUriPermission(uri, Intent.FLAG_GRANT_READ_URI_PERMISSION)
                }
''', "", "late persistable URI grant")

# The switch/help text is entirely absent until a custom background has been saved.
main = replace_once(main,
'''        appearance.addView(text("按钮颜色", 12, true, Color.rgb(75, 91, 118)), margin(bottom = 5))
        val autoAccentSwitch = MaterialSwitch(this).apply {
            text = "自动适配背景主色"
            isChecked = autoButtonColorEnabled
        }
        autoAccentSwitch.setOnCheckedChangeListener { _, checked ->
            if (checked) {
                if (DownloadTaskStore.backgroundUri(this@MainActivity).isBlank()) {
                    autoAccentSwitch.isChecked = false
                    toast("请先导入背景图片")
                } else {
                    autoButtonColorEnabled = true
                    DownloadTaskStore.setAutoButtonColor(this@MainActivity, true)
                    refreshAutoButtonColor()
                    if (!autoButtonColorEnabled) autoAccentSwitch.isChecked = false
                }
            } else {
                autoButtonColorEnabled = false
                DownloadTaskStore.setAutoButtonColor(this@MainActivity, false)
                buttonAccentColor = DownloadTaskStore.buttonColor(this@MainActivity)
                applyButtonAccent(page)
            }
        }
        appearance.addView(autoAccentSwitch, margin(bottom = 5))
        appearance.addView(text("开启后会提取当前背景的主要颜色；更换背景时会重新适配。手动调色会自动切回自定义颜色。", 10, false, Color.rgb(122, 132, 150)), margin(bottom = 7))''',
'''        appearance.addView(text("按钮颜色", 12, true, Color.rgb(75, 91, 118)), margin(bottom = 5))
        var autoAccentSwitch: MaterialSwitch? = null
        if (DownloadTaskStore.backgroundUri(this).isNotBlank()) {
            val switch = MaterialSwitch(this).apply {
                text = "自动适配背景主色"
                isChecked = autoButtonColorEnabled
            }
            autoAccentSwitch = switch
            switch.setOnCheckedChangeListener { _, checked ->
                if (checked) {
                    autoButtonColorEnabled = true
                    DownloadTaskStore.setAutoButtonColor(this@MainActivity, true)
                    refreshAutoButtonColor()
                    if (!autoButtonColorEnabled) switch.isChecked = false
                } else {
                    autoButtonColorEnabled = false
                    DownloadTaskStore.setAutoButtonColor(this@MainActivity, false)
                    buttonAccentColor = DownloadTaskStore.buttonColor(this@MainActivity)
                    applyButtonAccent(page)
                }
            }
            appearance.addView(switch, margin(bottom = 5))
            appearance.addView(text("开启后会提取当前背景的主要颜色；更换背景时会重新适配。手动调色会自动切回自定义颜色。", 10, false, Color.rgb(122, 132, 150)), margin(bottom = 7))
        }''', "auto-accent visibility")

# Remove the preview widget entirely; keep the RGB sliders and restore-default control.
main = replace_once(main,
'''        val colorPreview = MaterialButton(this).apply {
            text = "按钮颜色预览"; isAllCaps = false
            backgroundTintList = ColorStateList.valueOf(buttonAccentColor)
            setTextColor(if (Color.luminance(buttonAccentColor) < 0.45f) Color.WHITE else Color.BLACK)
        }
        palette.addView(colorPreview, margin(bottom = 7))
''', "", "button color preview control")
main = main.replace("            autoAccentSwitch.isChecked = false\n", "            autoAccentSwitch?.isChecked = false\n", 1)
main = main.replace("            colorPreview.backgroundTintList = ColorStateList.valueOf(buttonAccentColor)\n", "", 1)
main = main.replace("            colorPreview.setTextColor(if (Color.luminance(buttonAccentColor) < 0.45f) Color.WHITE else Color.BLACK)\n", "", 1)

if "colorPreview" in main or "按钮颜色预览" in main:
    raise SystemExit("Button preview code remains")
if "setSingleChoiceItems(labels, checked)" not in main or 'showFormatPicker(kind)' not in main:
    raise SystemExit("Format category chooser did not install")
if 'App version:' not in main or 'Regex("(?im)^App version:' not in main:
    raise SystemExit("Release asset app-version detection did not install")
if 'backgroundPicker.launch("image/*")' not in main:
    raise SystemExit("GetContent picker launch did not install")

# Keep the format-category controls readable on narrow screens.
main = replace_once(main,
'''                val selected = formats.getOrNull(selectedFormatIndex)?.takeIf { it.kind == kind }
                text = when {
                    count == 0 -> "$title\\n暂无可用格式"
                    selected != null -> "$title\\n${selected.label}"
                    else -> "$title\\n选择格式（$count 种）"
                }
                isAllCaps = false
                maxLines = 2
                ellipsize = android.text.TextUtils.TruncateAt.END
                textSize = 12f
                minWidth = 0
                minHeight = dp(58)''',
'''                val selected = formats.getOrNull(selectedFormatIndex)?.takeIf { it.kind == kind }
                val selectedSummary = selected?.label?.split(" · ")?.take(2)?.joinToString(" · ")?.take(22).orEmpty()
                text = when {
                    count == 0 -> "$title\\n暂无可用格式"
                    selected != null -> "$title\\n$selectedSummary"
                    else -> "$title\\n选择格式（$count 种）"
                }
                isAllCaps = false
                maxLines = 2
                ellipsize = android.text.TextUtils.TruncateAt.END
                textSize = 10.5f
                minWidth = 0
                minHeight = dp(64)''',
"compact format category summary")
main = main.replace("                height = dp(62)\n                setMargins(dp(3), dp(3), dp(3), dp(3))", "                height = dp(68)\n                setMargins(dp(3), dp(3), dp(3), dp(3))", 1)

# Do not repeat the selected format label beside the real stream format.
main = replace_once(main,
'''        body.addView(detail, margin(bottom = 7))''',
'''        body.addView(detail, margin(bottom = 7))''',
"task detail remains a separate row")
main = main.replace('        header.addView(clear)\n        header.addView(clear)\n', '        header.addView(clear)\n', 1)
main = replace_once(main,
'''        views.status.text = "${task.status} · ${task.formatLabel}"
        views.mediaInfo.text = task.mediaInfo
        views.mediaInfo.visibility = if (task.mediaInfo.isNotBlank()) View.VISIBLE else View.GONE''',
'''        views.status.text = task.status
        val actualFormat = task.mediaInfo.ifBlank { task.formatLabel }
        views.mediaInfo.text = actualFormat
        views.mediaInfo.visibility = if (actualFormat.isNotBlank()) View.VISIBLE else View.GONE''',
"deduplicate task format rows")

# Replace notifications with a rich collapsed line and expanded BigTextStyle.
service_path = root / "app/src/main/java/com/downkit/android/DownloadService.kt"
service = service_path.read_text(encoding="utf-8")
if "private fun buildDownKitNotification" not in service:
    helper = '''private fun buildDownKitNotification(
    context: Context, task: DownloadTask?, progress: Int = task?.progress ?: 0, status: String = task?.status ?: "正在连接"
): Notification {
    val bytes = task?.let {
        File(context.filesDir, "downloads/${it.id}").walkTopDown().filter { file -> file.isFile }.sumOf { file -> file.length() }
    } ?: 0L
    val written = when {
        bytes >= 1024L * 1024L * 1024L -> String.format("%.1f GB", bytes / 1073741824.0)
        bytes >= 1024L * 1024L -> String.format("%.1f MB", bytes / 1048576.0)
        bytes >= 1024L -> String.format("%.1f KB", bytes / 1024.0)
        bytes > 0 -> "$bytes B"
        else -> "大小暂未统计"
    }
    val media = task?.mediaInfo?.takeIf { it.isNotBlank() } ?: task?.formatLabel.orEmpty()
    val fragment = task?.fragmentInfo.orEmpty()
    val detail = task?.detail.orEmpty()
    val progressText = if (progress > 0) "$progress%" else status
    val mediaShort = media.split(" · ").take(2).joinToString(" · ")
    val detailShort = detail.removePrefix("已下载 ")
    val speedEta = listOf(
        task?.speed?.takeIf { it.isNotBlank() }?.let { "速度 $it" },
        task?.eta?.takeIf { it.isNotBlank() }?.let { "剩余 $it" }
    ).filterNotNull().joinToString(" · ")
    val compact = listOf(mediaShort, progressText, detailShort).filter { it.isNotBlank() }.joinToString(" · ").take(110)
    val expanded = listOf(
        "状态：$status",
        media,
        fragment,
        detail,
        "进度：$progressText",
        speedEta,
        "已写入文件：$written"
    ).filter { it.isNotBlank() }.joinToString("\\n")
    val open = PendingIntent.getActivity(
        context, 0, Intent(context, MainActivity::class.java), PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
    )
    return NotificationCompat.Builder(context, "downkit_downloads")
        .setSmallIcon(R.drawable.ic_stat_download)
        .setContentTitle((task?.title ?: "DownKit").take(72))
        .setContentText(compact)
        .setStyle(NotificationCompat.BigTextStyle().setBigContentTitle(task?.title ?: "DownKit").bigText(expanded))
        .setSubText("DownKit 下载进度")
        .setContentIntent(open)
        .setOngoing(status !in setOf("已完成", "已取消", "失败"))
        .setOnlyAlertOnce(true)
        .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
        .setProgress(100, progress.coerceIn(0, 100), progress <= 0 || status in setOf("连接网站", "正在合并/整理", "正在保存"))
        .build()
}
'''
    service = service.replace("class DownloadService : Service() {", helper + "\\n\\nclass DownloadService : Service() {", 1)
service = replace_once(service,
'''            val notification = buildNotification(firstTask?.title ?: "DownKit", 0, "正在连接")''',
'''            val notification = buildDownKitNotification(this, firstTask, 0, "正在连接")''',
"initial rich notification")
start = service.find("    private fun buildNotification(")
end = service.find("    private fun updateNotification", start)
if start >= 0 and end > start:
    service = service[:start] + service[end:]
service = replace_once(service,
'''        manager.notify(NOTIFICATION_ID, buildNotification(task.title, task.progress, task.status))''',
'''        manager.notify(NOTIFICATION_ID, buildDownKitNotification(this, task))''',
"service notification update")
service = replace_once(service,
'''            val notification = NotificationCompat.Builder(context, CHANNEL_ID)
                .setSmallIcon(R.drawable.ic_stat_download)
                .setContentTitle(task.title.take(72))
                .setContentText(if (task.progress in 1..99) "${task.progress}%" else task.status)
                .setContentIntent(open).setOngoing(true).setOnlyAlertOnce(true)
                .setProgress(100, task.progress.coerceIn(0, 100), task.progress <= 0).build()
            manager.notify(NOTIFICATION_ID, notification)''',
'''            manager.notify(NOTIFICATION_ID, buildDownKitNotification(context, task))''',
"rich notification refresh path")
service_path.write_text(service, encoding="utf-8")

# Report actual stream extension, keep audio streams from inheriting a video resolution,
# and avoid repeating extension/format ID in the detail row.
bridge_path = root / "app/src/main/python/bridge.py"
bridge = bridge_path.read_text(encoding="utf-8")
bridge = replace_once(bridge,
'''            width = info.get("width")
            height = info.get("height")
            resolution = info.get("resolution")
            if width and height:
                resolution = f"{int(width)}×{int(height)}"
            elif height:
                resolution = f"{int(height)}p"
            elif vcodec == "none":
                resolution = "音频"
            else:
                resolution = resolution or "分辨率未知"''',
'''            width = info.get("width")
            height = info.get("height")
            resolution = info.get("resolution")
            if vcodec == "none":
                resolution = "音频"
            elif width and height:
                resolution = f"{int(width)}×{int(height)}"
            elif height:
                resolution = f"{int(height)}p"
            else:
                resolution = resolution or "分辨率未知"''',
"audio resolution display")
bridge = replace_once(bridge,
'''            if stage == "finished":
                detail = f"{stream_kind} {format_id}.{ext} 已完成 · {downloaded_text} · 正在检查下一个流或准备合并"
            elif stage == "error":
                detail = f"{stream_kind} {format_id}.{ext} 下载失败 · {status.get('error') or '请查看任务错误信息'}"
            else:
                detail = f"{stream_kind} · 格式 {format_id}.{ext} · {fragment_text} · {downloaded_text}/{total_text} · {speed}"
                if eta:
                    detail += f" · 预计剩余 {eta}"''',
'''            if stage == "finished":
                detail = f"已下载 {downloaded_text} · 正在检查下一个流或准备合并"
            elif stage == "error":
                detail = f"下载失败 · {status.get('error') or '请查看任务错误信息'}"
            else:
                detail = f"已下载 {downloaded_text}/{total_text}"''',
"deduplicate per-task progress detail")
bridge_path.write_text(bridge, encoding="utf-8")
main_path.write_text(main, encoding="utf-8")
gradle_path.write_text(gradle, encoding="utf-8")
print("DownKit 1.1.3 replacement fixes applied (versionCode 9)")
