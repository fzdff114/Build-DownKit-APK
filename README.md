# DownKit Android

DownKit 是基于 yt-dlp 的 Android ARM64 视频/音频下载器。

## 下载应用

**当前测试版：** [DownKit 1.0.0 (ARM64 Debug)](https://github.com/fzdff114/Build-DownKit-APK/releases/tag/v1.0.0)

直接下载：[app-debug.apk](https://github.com/fzdff114/Build-DownKit-APK/releases/download/v1.0.0/app-debug.apk)

校验文件：[SHA256SUMS.txt](https://github.com/fzdff114/Build-DownKit-APK/releases/download/v1.0.0/SHA256SUMS.txt)

当前版本面向 ARM64（arm64-v8a）安卓设备，APK 为 Debug 签名测试版，尚非正式发行签名版本。

## 从源码构建

将 `DownKit-Android-source.zip` 上传到仓库根目录，文件名保持不变。然后进入 **Actions → Build DownKit APK** 查看自动构建结果。构建成功后，Artifacts 中会提供 APK 压缩包。

## 发布流程

仓库的 **Publish DownKit APK Release** 工作流负责把已验证的 ARM64 APK 发布到 GitHub Releases，并附带 SHA-256 校验文件。
