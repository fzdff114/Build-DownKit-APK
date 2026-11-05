#!/usr/bin/env python3
"""Patch existing DownKit 1.1.1 without changing version, application ID or signing."""
from pathlib import Path
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")

def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f"Missing source anchor: {label}")
    return text.replace(old, new, 1)

# Short launcher label.
strings_path = root / "app/src/main/res/values/strings.xml"
strings = replace_once(
    strings_path.read_text(encoding="utf-8"),
    '<string name="app_name">DownKit 视频与音频下载器</string>',
    '<string name="app_name">DownKit</string>',
    "short app name",
)
strings_path.write_text(strings, encoding="utf-8")

manifest_path = root / "app/src/main/AndroidManifest.xml"
manifest = replace_once(
    manifest_path.read_text(encoding="utf-8"),
    'android:label="DownKit 视频与音频下载器"',
    'android:label="@string/app_name"',
    "manifest label",
)
manifest_path.write_text(manifest, encoding="utf-8")

main_path = root / "app/src/main/java/com/downkit/android/MainActivity.kt"
main = main_path.read_text(encoding="utf-8")

# Proxy field: a separate label and only one hint inside the edit field.
old_proxy = '''        val proxyLayout = TextInputLayout(this).apply {
            hint = "代理地址（可选）"
            boxBackgroundMode = TextInputLayout.BOX_BACKGROUND_OUTLINE
        }
        proxyField = TextInputEditText(this).apply {
            setSingleLine(true); textSize = 14f; hint = "http://127.0.0.1:7890"
            setText(DownloadTaskStore.proxy(this@MainActivity))
        }
        proxyLayout.addView(proxyField)
        network.addView(proxyLayout, margin(bottom = 8))'''
new_proxy = '''        network.addView(text("代理地址（可选）", 12, true, Color.rgb(75, 91, 118)), margin(bottom = 6))
        val proxyLayout = TextInputLayout(this).apply {
            setHintEnabled(false)
            boxBackgroundMode = TextInputLayout.BOX_BACKGROUND_OUTLINE
        }
        proxyField = TextInputEditText(this).apply {
            setSingleLine(true)
            maxLines = 1
            setHorizontallyScrolling(true)
            minHeight = dp(54)
            gravity = Gravity.CENTER_VERTICAL
            includeFontPadding = true
            setPadding(dp(12), dp(10), dp(12), dp(10))
            textSize = 14f
            inputType = android.text.InputType.TYPE_CLASS_TEXT or android.text.InputType.TYPE_TEXT_VARIATION_URI or android.text.InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS
            imeOptions = android.view.inputmethod.EditorInfo.IME_ACTION_DONE
            hint = "例如 http://127.0.0.1:7890"
            setText(DownloadTaskStore.proxy(this@MainActivity))
        }
        proxyLayout.addView(proxyField)
        network.addView(proxyLayout, LinearLayout.LayoutParams(-1, dp(62)).apply { bottomMargin = dp(10) })'''
main = replace_once(main, old_proxy, new_proxy, "proxy field layout")

# Common page transition: short, subtle fade/slide; no changes to scrolling or state.
main = replace_once(
    main,
    "    private fun renderHome() {",
    '''    private fun showPage(content: View) {
        page.animate().cancel()
        content.animate().cancel()
        content.alpha = 0f
        content.translationY = dp(7).toFloat()
        page.removeAllViews()
        page.addView(content, FrameLayout.LayoutParams(-1, -1))
        content.animate()
            .alpha(1f)
            .translationY(0f)
            .setDuration(190)
            .setInterpolator(android.view.animation.DecelerateInterpolator())
            .start()
    }

    private fun setParseLoading(active: Boolean) {
        if (active) {
            if (parsePulseAnimator == null) {
                parsePulseAnimator = android.animation.ValueAnimator.ofFloat(1f, 0.58f).apply {
                    duration = 680
                    repeatMode = android.animation.ValueAnimator.REVERSE
                    repeatCount = android.animation.ValueAnimator.INFINITE
                    addUpdateListener { parseStageView?.alpha = it.animatedValue as Float }
                    start()
                }
            }
        } else {
            parsePulseAnimator?.cancel()
            parsePulseAnimator = null
            parseStageView?.alpha = 1f
        }
    }

    private fun renderHome() {''',
    "page and parse animation helpers",
)

# All three tab renderers use the same transition helper.
main = main.replace(
    '''        page.removeAllViews()
        page.addView(scroll, FrameLayout.LayoutParams(-1, -1))''',
    '''        showPage(scroll)''',
)
if main.count("showPage(scroll)") != 3:
    raise SystemExit(f"Expected 3 tab swaps through showPage, got {main.count('showPage(scroll)')}")

# Keep parse/loading animation alive when switching away and back.
main = replace_once(
    main,
    "    private var parseProgressBar: ProgressBar? = null",
    "    private var parseProgressBar: ProgressBar? = null\n    private var parsePulseAnimator: android.animation.ValueAnimator? = null",
    "parse pulse animator field",
)
main = replace_once(
    main,
    "    private val taskCardViews = linkedMapOf<String, TaskCardViews>()",
    "    private val taskCardViews = linkedMapOf<String, TaskCardViews>()\n    private val taskPulseAnimators = linkedMapOf<String, android.animation.ValueAnimator>()",
    "task pulse animator field",
)
main = replace_once(
    main,
    '            parseStageView?.text = "正在连接目标网站…"',
    '            parseStageView?.text = "正在连接目标网站…"\n            setParseLoading(true)',
    "restore parse animation after tab switch",
)
main = replace_once(
    main,
    '        parseProgressBar?.visibility = View.VISIBLE\n        parseStageView?.text = "① 检查链接 · 准备连接目标网站…"',
    '        parseProgressBar?.visibility = View.VISIBLE\n        setParseLoading(true)\n        parseStageView?.text = "① 检查链接 · 准备连接目标网站…"',
    "start parse animation",
)
main = replace_once(
    main,
    "                isParsing = false\n                parseButton?.isEnabled = true",
    "                isParsing = false\n                setParseLoading(false)\n                parseButton?.isEnabled = true",
    "stop parse animation",
)

# Pulse the task status while connecting/downloading/merging/saving.
main = replace_once(
    main,
    "    private fun updateTaskCard(task: DownloadTask) {",
    '''    private fun updateTaskPulse(taskId: String, statusView: TextView, active: Boolean) {
        if (active) {
            if (!taskPulseAnimators.containsKey(taskId)) {
                val animator = android.animation.ValueAnimator.ofFloat(1f, 0.62f).apply {
                    duration = 720
                    repeatMode = android.animation.ValueAnimator.REVERSE
                    repeatCount = android.animation.ValueAnimator.INFINITE
                    addUpdateListener { statusView.alpha = it.animatedValue as Float }
                }
                taskPulseAnimators[taskId] = animator
                animator.start()
            }
        } else {
            taskPulseAnimators.remove(taskId)?.cancel()
            statusView.alpha = 1f
        }
    }

    private fun updateTaskCard(task: DownloadTask) {''',
    "download activity animation helper",
)
main = replace_once(
    main,
    '        val active = task.status in setOf("连接网站", "下载中", "正在合并/整理", "正在保存")\n        views.progress.visibility',
    '        val active = task.status in setOf("连接网站", "下载中", "正在合并/整理", "正在保存")\n        updateTaskPulse(task.id, views.status, active)\n        views.progress.visibility',
    "activate download pulse",
)
main = replace_once(
    main,
    "        val previousScrollY = taskScroll?.scrollY ?: taskScrollY\n        val column = LinearLayout(this).apply {",
    "        val previousScrollY = taskScroll?.scrollY ?: taskScrollY\n        taskPulseAnimators.values.forEach { it.cancel() }\n        taskPulseAnimators.clear()\n        val column = LinearLayout(this).apply {",
    "dispose old task-view animators before rebuilding cards",
)
main = replace_once(
    main,
    "        handler.removeCallbacks(refreshLoop)\n        if (currentActivity === this) currentActivity = null",
    "        handler.removeCallbacks(refreshLoop)\n        parsePulseAnimator?.cancel()\n        parsePulseAnimator = null\n        taskPulseAnimators.values.forEach { it.cancel() }\n        taskPulseAnimators.clear()\n        if (currentActivity === this) currentActivity = null",
    "dispose animations on destroy",
)
main_path.write_text(main, encoding="utf-8")

# Do not bump versionCode or versionName: this is a replacement of the existing 1.1.1 release.
gradle = (root / "app/build.gradle.kts").read_text(encoding="utf-8")
if 'versionName = "1.1.1"' not in gradle or "versionCode = 5" not in gradle:
    raise SystemExit("Refusing to bump version; expected the current 1.1.1 build (versionCode 5)")
if "applicationId = \"com.downkit.android\"" not in gradle:
    raise SystemExit("Unexpected applicationId; refusing to rebuild")
if 'android:label="@string/app_name"' not in manifest:
    raise SystemExit("Manifest app label patch did not apply")

assert main.count("showPage(scroll)") == 3
assert "parsePulseAnimator" in main and "taskPulseAnimators" in main
print("DownKit 1.1.1 proxy/name/animation patch applied. Version and package ID unchanged.")
