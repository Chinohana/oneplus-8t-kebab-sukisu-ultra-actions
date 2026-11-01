# 2026-11-01 工具链与依赖更新

本次候选将 Android 平台 Clang 固定为 `clang-r614150`，对应 AOSP 预编译仓库提交 `a83b2dbffadbe45e7ec16e68498723a1e418fa19`；NDK 更新到 r30（`30.0.16248370`），Linux 压缩包按 Google 公布的 SHA-1 `5107f898313790e449e87eee2183d9a20602dee9` 校验。安装脚本、本地默认路径与使用者自定义构建入口同时更新。旧工具链保留。

## Manager 和源码依赖

最新 Release 为 [v4.3.0 / 41100](https://github.com/SukiSU-Ultra/SukiSU-Ultra/releases/tag/v4.3.0)。最新成功的 [Build Manager 41297360442](https://github.com/SukiSU-Ultra/SukiSU-Ultra/actions/runs/41297360442) 对应 main `56d45a19193a41bf42c8db655c9d2cfba44c48f1`，构建日志记录 3939 个 main 提交，版本计算为 `40000 + 3939 - 2815 = 41124`；附件文件名为 `SukiSU_v4.3.0_41124-release.apk`。

从 [Release 到该 Action](https://github.com/SukiSU-Ultra/SukiSU-Ultra/compare/v4.3.0...56d45a19193a41bf42c8db655c9d2cfba44c48f1) 存在实际修复与界面变化，故固定版本号 **41124**。与上一交付 Manager 41120 的 main `0fe8d052ab7f9c314f01c9d3451812115e424b69` 相比，修复 Miuix 导航栏模糊显示和主页状态卡背景拉伸，符合 Manager 交付条件。APK SHA-256：`e1bfece51f8bc79832f4b338ec8724c8696ef60a9bb4f1ed3e3ba393e4ec4302`。

builtin 仍为 `b16e899a555e9b96aa1225f049cd7274820ca5b8`。LineageOS `lineage-24.0` 与 AnyKernel3 仍为原 pin。SUSFS 上游最新 `0d5b1ceb4ca4cddbe59d04233f4425a83030aa71` 包含 priority UID 解析调整，但其间还包含上游标记为实验性、未完成的 SELinux hide 重构；本次先保留现有 `ee155a1ad4219804a7c54cb39dd4fa1b5c2a3fa4`，不把未移植的新源码记作已同步。

工具链下载及完整构建尚待验证；本记录不代表真机验收。
