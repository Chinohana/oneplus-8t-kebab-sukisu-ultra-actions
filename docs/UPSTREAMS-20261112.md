# 2026-11-12 上游同步

LineageOS `lineage-24.0` 从 `98a7970af93b7e01ee77156e7fa0eb7e059a57f0` 更新至 `078365e5318de0a30a41f9707070b610bcd20f13`。GitHub 比较结果为 ahead，共 60 个提交，包含相机、adsprpc 等驱动的边界检查和内存安全修复。固定内核补丁已在新源码上按顺序检查。

SukiSU builtin 从 `b16e899a555e9b96aa1225f049cd7274820ca5b8` 更新至 `6076949f26bf51325bd5e4e790b699c6f2a6acb5`。上游重写 mount_hide 并修复旧内核 SELinux 兼容；原来由本项目维护的 proc 文件系统判断和旧内核 SID 缓存调用已由上游提供。兼容补丁按新源码整理，完整配置显式启用新的 `CONFIG_KSU_SUSFS_PRIORITY_UID_FILTER`。

## Manager 版本

最新 Release 为 [v4.3.0-r2](https://github.com/SukiSU-Ultra/SukiSU-Ultra/releases/tag/v4.3.0-r2)，普通 APK 为 `SukiSU_v4.3.0-r2_41150-release.apk`，标签指向 `645ef9860b9b7f900bb5d1b27e224f2c311d39c0`。最新成功的主线正式签名 [Build Manager 42997964176](https://github.com/SukiSU-Ultra/SukiSU-Ultra/actions/runs/42997964176) 使用 main `3af6085d0d26e73ffd1a3e7b34362435dcfb5a03`；构建日志记录主线提交数 3991，`40000 + 3991 - 2815 = 41176`，APK 实际名称为 `SukiSU_v4.3.0-r2_41176-release.apk`。

[Release 到 Action 的差异](https://github.com/SukiSU-Ultra/SukiSU-Ultra/compare/v4.3.0-r2...3af6085d0d26e73ffd1a3e7b34362435dcfb5a03) 包含主题商店、外观界面以及 Manager 安全和崩溃修复，故驱动版本与兼容补丁默认值固定为 **41176**。翻译 PR 的 Action 42997994991 生成 41178，但使用临时签名；按维护者要求不纳入版本选择或交付。

相对上一已交付 Manager 41124 的 main `56d45a19193a41bf42c8db655c9d2cfba44c48f1`，41176 包含功能、界面与修复更新，符合交付条件。普通主线 APK SHA-256 为 `5055e58f86b8b22c6368f65cccd05b8dc98afbcc594f532f30ee3ff85196675f`。Manager main 与 builtin 分支独立记录。

## SUSFS 和工具链

SUSFS 上游已发布 v2.4.0，最新提交为 `69b8e734920b8f9ed885ab8d112969719698e242`。这套变化包含 SELinux hide 重构，需要与本项目的 4.19 专用移植逐项整合；本次内核和 SukiSU 候选继续使用现有 SUSFS v2.3.0 `ee155a1ad4219804a7c54cb39dd4fa1b5c2a3fa4`，不将尚未移植的 2.4.0 记为已同步。AnyKernel3、Clang 和 NDK 保持原 pin。

本次候选尚待完整构建和真机验证。
