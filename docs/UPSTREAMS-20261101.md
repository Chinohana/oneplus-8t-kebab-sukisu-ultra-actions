# 2026-11-01 上游同步

SukiSU builtin 从 `b59170724cdc05bf5dee8d8a8b182c5f1ddd60e3` 更新到 `b16e899a555e9b96aa1225f049cd7274820ca5b8`，包含扩展 ABI 2 枚举、SELinux hide 策略解析修复及 Clang GKI 构建修复。4.19 使用现有 SELinux hide 移植，不能据此声称已采用新版内核专用的全部解析路径。

SUSFS 从 `27e0a0e42745991ba09d6f96a97bf4b83f41a012` 更新到 `ee155a1ad4219804a7c54cb39dd4fa1b5c2a3fa4`，移植 priority UID filter 的两处 RCU 同步及 worker 调度修复。最新分支后续的 `83b341e` 明确标注 SELinux hide 重构为 experimental、partially done；本次停在重构前的修复提交，保留现有完整功能方案。LineageOS、AnyKernel3 与 SM8250 参考提交保持原 pin。

## Manager

最新 Release [v4.3.0](https://github.com/SukiSU-Ultra/SukiSU-Ultra/releases/tag/v4.3.0) 的普通 APK 为 `SukiSU_v4.3.0_41100-release.apk`，源码为 `e67b14e6bbbbd3e67f24df658a01d3e73a64159c`。最新成功的 [Build Manager 41221737517](https://github.com/SukiSU-Ultra/SukiSU-Ultra/actions/runs/41221737517) 对应 main `0fe8d052ab7f9c314f01c9d3451812115e424b69`；日志记录 3935 个 main 提交，`40000 + 3935 - 2815 = 41120`。

[Release 到 Action](https://github.com/SukiSU-Ultra/SukiSU-Ultra/compare/v4.3.0...0fe8d052ab7f9c314f01c9d3451812115e424b69) 包含主题包导入导出、文件关联、WebUI File 接口、动态管理器重复应用崩溃和缺失图标修复，故驱动及补丁默认版本选用 **41120**。builtin 与 Manager main 分别固定，不以 Manager 变化代替驱动源码核验。

相对上一交付 Manager 41097 的 main `080ba098902c1ea8f09748536f9d920329e2f7ce`，上述修复和 UI 功能属于实质更新，因此本次下载普通 Manager：`SukiSU_v4.3.0_41120-release.apk`，SHA-256 为 `b95520220660df90d4cb4d3e6ab924aac5c820016ef6c350fd107539da8e1d74`。

## 工具链

按本次要求保留 Clang r563880（归档提交 `6f88d37dd82ba741ca279539d44bb7da27ab1844`）与 NDK r27c（27.2.12479018），不下载或切换编译器。核对 [NDK 官方发布记录](https://github.com/android/ndk/releases) 中 r27 至 r30 的说明，未发现明确标注重大漏洞或 CVE 的升级要求；r30 记录了 LTO 运行时崩溃、误编译等修复。这一结论只限所查公告，不能证明旧工具链没有漏洞。

## 验证

扩展 ABI 宿主测试已在本次 builtin 源码上通过，覆盖 ABI 2 枚举、越界及空指针，同时保留旧客户端与结构布局检查。内核编译和真机验收结果另行记录。
