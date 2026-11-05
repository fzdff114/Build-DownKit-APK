# DownKit — 开源 Android 视频与音频下载器

DownKit 是面向 Android 用户的开源媒体下载工具，使用 [yt-dlp](https://github.com/yt-dlp/yt-dlp) 解析受支持的网站，提供格式选择、下载队列、音视频合并和本地保存功能。

## 下载

**最新发行版：** [GitHub Releases](https://github.com/fzdff114/Build-DownKit-APK/releases)

当前目标版本：**DownKit 1.1.1（ARM64）**

发行版页面提供 Android APK、SHA-256 校验文件和完整 Android Studio 源码压缩包。大多数 64 位 ARM 手机请选择 ARM64 APK。

## 功能

- 解析视频链接并显示标题、封面、作者、时长和可用格式。
- 双列格式选择，支持视频、音频及兼容优先的单文件下载；格式列表随页面一起滚动，不使用嵌套滚动区域。
- 下载队列、原位更新的实时进度、连接状态、速度、预计剩余时间、取消和重试；进度刷新不会重建任务列表。
- 分离音视频时通过内置 FFmpeg 合并，并显示实际下载格式、分片进度、合并和保存阶段；当网站临时撤下所选格式时，会自动尝试兼容格式。
- 切换下载、任务和设置页面时保留当前输入链接及解析结果。
- 可导入本机 Cookie、设置代理、播放列表下载和保存目录。
- 连接 GitHub Releases 检查更新，下载并校验新 APK，再交给 Android 安装程序完成升级。
- 使用固定 Release 签名密钥，后续版本可在相同签名下原位升级。

## 网站兼容性

项目包含 yt-dlp 的大量站点提取器，但不能保证所有网站永久可用。网站可能调整页面、API、登录流程、地区限制和反自动化策略；部分内容需要用户自己的 Cookie 或特定网络环境。DRM 加密媒体和用户无权访问的内容不在支持范围内。

## 安装与更新

从 [Releases](https://github.com/fzdff114/Build-DownKit-APK/releases) 下载 APK。应用内「设置 → 应用更新」可检查 GitHub 上的最新发行版，下载后会验证 SHA-256（发行版提供时）并打开 Android 安装程序。Android 仍会要求用户确认安装；普通应用不能静默替换自身。

**签名说明：** 1.0.x 是临时 CI Debug 签名。首次切换到固定 Release 签名的 1.1.1 时，Android 可能要求先卸载旧版；1.1.1 之后使用同一私钥签名的版本即可原位更新。请勿清除或丢失 Release 签名密钥。

## 从源码构建

发行版内附 DownKit-Android-1.1.1-source.zip。构建需要 JDK 21、Android SDK Platform 36、NDK 27.2.12479018、CMake 3.22.1 和 Python 3.13。将源码目录用 Android Studio 打开，或在项目目录运行：

    ./gradlew --no-daemon assembleDebug

发布正式更新包时，需要在 GitHub Actions 中配置固定签名密钥。详见发行签名配置：
https://github.com/fzdff114/Build-DownKit-APK/blob/main/docs/release-signing.md

## 负责任地使用

请仅下载自己拥有或被授权保存的内容，并遵守目标网站服务条款及当地法律。导入的 Cookie 只保存在应用私有目录；不要与他人分享 Cookie 或签名密钥。
