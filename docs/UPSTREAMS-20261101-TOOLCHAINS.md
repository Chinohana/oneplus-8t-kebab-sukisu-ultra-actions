# 2026-11-01 工具链与依赖更新

本次候选将 Android 平台 Clang 固定为 `clang-r614150`，对应 AOSP 预编译仓库提交 `a83b2dbffadbe45e7ec16e68498723a1e418fa19`；NDK 更新到 r30（`30.0.16248370`），Linux 压缩包按 Google 公布的 SHA-1 `5107f898313790e449e87eee2183d9a20602dee9` 校验。安装脚本、本地默认路径与使用者自定义构建入口同时更新。旧工具链保留。

## Manager 和源码依赖

最新 Release 为 [v4.3.0 / 41100](https://github.com/SukiSU-Ultra/SukiSU-Ultra/releases/tag/v4.3.0)。最新成功的 [Build Manager 41297360442](https://github.com/SukiSU-Ultra/SukiSU-Ultra/actions/runs/41297360442) 对应 main `56d45a19193a41bf42c8db655c9d2cfba44c48f1`，构建日志记录 3939 个 main 提交，版本计算为 `40000 + 3939 - 2815 = 41124`；附件文件名为 `SukiSU_v4.3.0_41124-release.apk`。

从 [Release 到该 Action](https://github.com/SukiSU-Ultra/SukiSU-Ultra/compare/v4.3.0...56d45a19193a41bf42c8db655c9d2cfba44c48f1) 存在实际修复与界面变化，故固定版本号 **41124**。与上一交付 Manager 41120 的 main `0fe8d052ab7f9c314f01c9d3451812115e424b69` 相比，修复 Miuix 导航栏模糊显示和主页状态卡背景拉伸，符合 Manager 交付条件。APK SHA-256：`e1bfece51f8bc79832f4b338ec8724c8696ef60a9bb4f1ed3e3ba393e4ec4302`。

builtin 仍为 `b16e899a555e9b96aa1225f049cd7274820ca5b8`。LineageOS `lineage-24.0` 与 AnyKernel3 仍为原 pin。SUSFS 上游最新 `0d5b1ceb4ca4cddbe59d04233f4425a83030aa71` 包含 priority UID 解析调整，但其间还包含上游标记为实验性、未完成的 SELinux hide 重构；本次先保留现有 `ee155a1ad4219804a7c54cb39dd4fa1b5c2a3fa4`，不把未移植的新源码记作已同步。

## 本地验证

Clang 归档 SHA-256 为 `554c9a97e23ced48aacb7bc1184911e9767130e3fb7185dd86516ad8d3a49e6d`；gzip 完整性检查通过，`clang-23`、`lld`、`llvm-ar` 和 `llvm-nm` 的 Git 对象哈希与固定 AOSP 提交一致。NDK r30 的 SHA-256 为 `753611f410d002cfcd3f3dc2ef49aad532089d3180b436c060a90bf0fcb64df2`，版本及官方 SHA-1 检查通过。

完整配置构建 `local-full-20261101-191139` 使用 builder `cd6863a2b50a4dbe635711f508fc1d3892e8f2d7`。预检、源码与补丁审计、内核编译、产物审计、工具编译、打包和导出校验通过。新 Clang 首次构建的 make 耗时 280.74 秒；本地构建入口 14 项测试、单一配置 2 项测试及发布工具 12 项测试通过。

Image SHA-256 为 `38ceeac38906401b418bfe653c9a77163387c3e163de76b65254f311c1596f3d`，安装包 SHA-256 为 `fba63560e0918dbf99047da5193020d2359b9052cff8be4af7970bc17e3e79b8`。产物尚未进行真机测试或正式验收。
