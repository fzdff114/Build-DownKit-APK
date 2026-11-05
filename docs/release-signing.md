# GitHub Actions 固定签名配置

DownKit 1.1.0 开始使用固定的 Android Release 签名密钥。Android 只有在新 APK 使用与已安装应用相同的签名证书时，才允许覆盖升级。

## 一次性配置

在 GitHub 仓库打开 **Settings → Secrets and variables → Actions → New repository secret**，添加以下四项：

| Secret 名称 | 内容 |
|---|---|
| DOWNKIT_KEYSTORE_BASE64 | 私有签名密钥文件的完整 Base64 文本 |
| DOWNKIT_STORE_PASSWORD | keystore 密码 |
| DOWNKIT_KEY_ALIAS | 密钥别名 |
| DOWNKIT_KEY_PASSWORD | 私钥密码 |

密钥文件与密码由项目维护者离线生成，并通过私密渠道保存。不要把 keystore、Base64 内容或密码提交到公开仓库、Issue、Pull Request 或发行说明中。

## 重要事项

- 私钥必须保留至少一个离线备份。丢失私钥后，无法再为相同应用 ID 发布可原位升级的 APK。
- 所有未来 Release 都必须使用同一套签名密钥；不要重新生成或替换。
- 1.0.x 测试版由临时 CI Debug 密钥签名。首次安装 1.1.0 时，Android 可能要求先卸载 1.0.x，再安装固定签名版；这次切换只需要做一次。
- 1.1.0 之后，由本工作流使用同一密钥签名的版本即可在原应用上升级。
- 应用内更新会从 GitHub Releases 下载 APK、检查 SHA-256，并交给 Android 系统安装器。系统仍会要求用户确认；普通应用无法静默安装更新。

配置完成后，进入 **Actions → Build DownKit APK → Run workflow**，构建并发布新的 ARM64 安装包。
