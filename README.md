# DownKit — Android 视频与音频下载器

DownKit 是面向 Android 用户的媒体下载工具，使用 [yt-dlp](https://github.com/yt-dlp/yt-dlp) 解析受支持的网站，提供格式选择、下载队列、音视频合并和本地保存功能。

## 下载应用

**最新发行版：** [GitHub Releases](https://github.com/fzdff114/Build-DownKit-APK/releases)

目标设备为 ARM64（arm64-v8a）的 Android 手机，请下载发行版中的 ARM64 APK。每个正式发行版同时提供完整 Android Studio 源码 ZIP 和 SHA-256 校验文件。

## 功能

- 解析视频链接并显示标题、封面、作者、时长和可用格式。
- 显示网站返回的真实媒体容器格式（MP4、WebM、MKV、M4A 等）及分辨率，不将所有媒体都标记为 MP4。
- 下载任务显示实际格式、分辨率、下载速度、进度、预计剩余时间，以及网站提供分片信息时的当前分片/总分片数。
- 下载通知仅显示文件名称和简洁的进度/状态。
- 下载队列、取消、失败重试和中断状态恢复。
- 分离音视频时通过内置 FFmpeg 合并。
- 设置中可导入背景图片并持久保存，支持恢复默认背景。
- 设置中可展开 RGB 调色面板调整按钮颜色；颜色选择会保存并在下次启动时恢复。
- 支持 Cookie 导入、代理设置、播放列表下载和保存目录选择。

## 网站兼容性

项目包含 yt-dlp 的大量站点提取器，但不能保证所有网站永久可用。网站可能调整页面、API、登录流程、地区限制和反自动化策略；部分内容需要用户自己的 Cookie 或特定网络环境。分片信息由目标网站提供，某些网站不会暴露精确的分片总数。DRM 加密媒体和用户无权访问的内容不在支持范围内。

## 安装与更新

从 [Releases](https://github.com/fzdff114/Build-DownKit-APK/releases) 下载 APK。应用内更新功能会检查 GitHub Releases，下载 APK 后交给 Android 系统安装器；系统仍会要求用户确认安装，普通应用不能静默替换自身。

**签名说明：** 1.1.0 起使用固定 Release 签名密钥。后续正式版本沿用相同的签名证书，可在已安装应用上原位升级。请勿丢失 Release 签名私钥，也不要将密钥或密码提交到公开仓库。

## 从源码构建

最新发行版内附完整源码 DownKit-Android-<version>-source.zip。构建需要 JDK 21、Python 3.13、Android SDK Platform 36、Build Tools 36.0.0、NDK 27.2.12479018 和 CMake 3.22.1。

在项目目录执行：

    ./gradlew --no-daemon assembleDebug

正式发布需要在 GitHub Actions Secrets 中配置固定签名所需的四项仓库密钥。名称为 DOWNKIT_KEYSTORE_BASE64、DOWNKIT_STORE_PASSWORD、DOWNKIT_KEY_ALIAS 和 DOWNKIT_KEY_PASSWORD。不要将其值写入公开文件。

## 负责任地使用

请仅下载自己拥有或被授权保存的内容，并遵守目标网站服务条款及当地法律。导入的 Cookie 与外观设置保存在应用私有数据中；不要分享 Cookie 或签名密钥。
