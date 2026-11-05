# DownKit Android

DownKit 是基于 yt-dlp 的 Android ARM64 视频/音频下载器。

## 下载应用

**当前测试版：** [DownKit 1.0.1 (ARM64 Debug)](https://github.com/fzdff114/Build-DownKit-APK/releases/tag/v1.0.1)

直接下载：[app-debug.apk](https://github.com/fzdff114/Build-DownKit-APK/releases/download/v1.0.1/app-debug.apk)

校验文件：[SHA256SUMS.txt](https://github.com/fzdff114/Build-DownKit-APK/releases/download/v1.0.1/SHA256SUMS.txt)

1.0.1 修复了 Chaquopy 的 Java String 数组桥接错误，该错误会导致分离音视频下载后在 FFmpeg 合并阶段失败。当前版本面向 ARM64（arm64-v8a）安卓设备，APK 为 Debug 签名测试版，尚非正式发行签名版本。

## 从源码构建

将 `DownKit-Android-source.zip` 上传到仓库根目录，文件名保持不变。然后进入 **Actions → Build DownKit APK** 查看自动构建结果。构建成功后，Artifacts 中会提供 APK 压缩包。

## 发布流程

仓库的 **Publish DownKit APK Release** 工作流会在构建成功后自动发布 ARM64 APK，并附带 SHA-256 校验文件。
