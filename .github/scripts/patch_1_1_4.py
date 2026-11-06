#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parents[2] / "DownKit-Android"
main_path = root / "app/src/main/java/com/downkit/android/MainActivity.kt"
gradle_path = root / "app/build.gradle.kts"
main = main_path.read_text(encoding="utf-8")
gradle = gradle_path.read_text(encoding="utf-8")

def replace_once(source, old, new, name):
    if old not in source:
        raise SystemExit("Missing expected source block: " + name)
    return source.replace(old, new, 1)

if 'versionName = "1.1.3"' not in gradle or "versionCode = 8" not in gradle:
    raise SystemExit("Expected DownKit 1.1.3/versionCode 8 baseline")
gradle = gradle.replace("versionCode = 8", "versionCode = 9", 1)
gradle = gradle.replace('versionName = "1.1.3"', 'versionName = "1.1.4"', 1)

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
        infoColumn.addView(formatGrid!!, LinearLayout.LayoutParams(-1, ViewGroup.LayoutParams.WRAP_CONTENT).apply { bottomMargin = dp(7) })''', "format category UI")

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
        formats = (0 until (formatArray?.length() ?: 0)).mapNotNull { index ->
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
                text = if (count > 0) "$title\\n选择格式（$count 种）" else "$title\\n暂无可用格式"
                isAllCaps = false
                maxLines = 2
                textSize = 12f
                minWidth = 0
                minHeight = dp(58)
                insetTop = 0
                insetBottom = 0
                isEnabled = count > 0
                setOnClickListener { showFormatPicker(kind) }
            }

        listOf(
            categoryButton("video", videoFormats.size, "视频下载"),
            categoryButton("audio", audioFormats.size, "音频下载")
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
        var checked = 0
        val title = if (kind == "audio") "选择音频格式" else "选择视频格式"
        val dialog = androidx.appcompat.app.AlertDialog.Builder(this)
            .setTitle(title)
            .setSingleChoiceItems(labels, checked) { _, which -> checked = which }
            .setNegativeButton("取消", null)
            .setPositiveButton("下载所选格式", null)
            .create()
        dialog.setOnShowListener {
            dialog.getButton(androidx.appcompat.app.AlertDialog.BUTTON_POSITIVE).setOnClickListener {
                selectedFormatIndex = formats.indexOf(choices[checked]).coerceAtLeast(0)
                dialog.dismiss()
                startDownload()
            }
        }
        dialog.show()
    }

'''
main = main[:start] + renderer + main[end:]

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
if 'backgroundPicker.launch("image/*")' not in main:
    raise SystemExit("GetContent picker launch did not install")

main_path.write_text(main, encoding="utf-8")
gradle_path.write_text(gradle, encoding="utf-8")
print("DownKit 1.1.4 fixes applied")
