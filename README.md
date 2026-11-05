# DownKit Android

DownKit 是基于 yt-dlp 的 Android ARM64 视频/音频下载器。

## 下载应用

**当前测试版：** [DownKit 1.0.2 (ARM64 Debug)](https://github.com/fzdff114/Build-DownKit-APK/releases/tag/v1.0.2)

直接下载：[app-debug.apk](https://github.com/fzdff114/Build-DownKit-APK/releases/download/v1.0.2/app-debug.apk)

校验文件：[SHA256SUMS.txt](https://github.com/fzdff114/Build-DownKit-APK/releases/download/v1.0.2/SHA256SUMS.txt)

1.0.2 修复了解析结果与下载任务 URL 未绑定造成的队列链接丢失，改为持久保存解析时的原始链接；编辑链接会使旧解析失效；新任务在启动下载前会校验并立即写入本机队列；任务卡显示已保存的链接。Bilibili 的提取器和封面/标题识别流程保留不变。

当前版本面向 ARM64（arm64-v8a）安卓设备，APK 为 Debug 签名测试版，尚非正式发行签名版本。

## 从源码构建

将 `DownKit-Android-source.zip` 上传到仓库根目录，文件名保持不变。然后进入 **Actions → Build DownKit APK** 查看自动构建结果。构建成功后，Artifacts 中会提供 APK 压缩包。

## 发布流程

仓库的 **Publish DownKit APK Release** 工作流会在构建成功后自动发布 ARM64 APK，并附带 SHA-256 校验文件。
