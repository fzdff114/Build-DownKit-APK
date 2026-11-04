# DownKit Android

这是 DownKit Android APK 的构建仓库。

## 上传源码包

将 ChatGPT 提供的 `DownKit-Android-source.zip` 上传到仓库根目录，文件名保持完全一致。

上传完成后，GitHub Actions 会自动构建；也可以进入 **Actions → Build DownKit APK → Run workflow** 手动启动。

## 下载 APK

构建成功后打开对应的 Actions 运行记录，在 **Artifacts** 区域下载 `DownKit-debug-apks`，解压后按设备架构安装：

- `app-arm64-v8a-debug.apk`：大多数 ARM64 安卓手机
- `app-x86_64-debug.apk`：x86_64 Android 设备

注意：该仓库的 Actions 负责云端构建，不会自动把 APK 安装到手机。构建失败时请打开运行记录查看具体日志。
