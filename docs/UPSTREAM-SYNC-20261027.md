# 上游同步记录：2026-10-27

本次将 SukiSU builtin 从 `ce75122bec7423e0f1fa06e3e9a174085c5231ab` 更新到 `0b666cad90f3a13cb4085f8c88e5144594e82030`，五位版本号从 41074 调为 41095。AnyKernel3 更新到 `08e9d1281f38019efcf8818e18525e55e679046f`。Clang 和 NDK 保持原固定版本。

## Manager 的选择

核对时，最新 Release 为 [v4.2.1-r2](https://github.com/SukiSU-Ultra/SukiSU-Ultra/releases/tag/v4.2.1-r2)，Manager 文件名为 `SukiSU_v4.2.1-r2_41068-release.apk`。最新成功的 [Build Manager run 40390221573](https://github.com/SukiSU-Ultra/SukiSU-Ultra/actions/runs/40390221573) 对应 main `96ceb4a42c50e27199a094264f62cfbafee77fa0`，下载的 Manager artifact 包含 `SukiSU_v4.2.1-r2_41095-release.apk`。

[Release 到该 Action 源码的比较](https://github.com/SukiSU-Ultra/SukiSU-Ultra/compare/v4.2.1-r2...96ceb4a42c50e27199a094264f62cfbafee77fa0) 包含静态 kstat 执行修复、配置对话框调整、priority UID 筛选界面、版本伪装设置、模块 ZIP 安装后删除选项、AnyKernel3 安装流程修复，以及 Android 12 及更早版本的 receiver 权限修复。这些属于实际功能、Bug 和 UI 更新，因此按项目规则选用 Action 的 **41095**。

该运行的 determine-version 日志确认 main 提交数为 3910，计算结果为 `40000 + 3910 - 2815 = 41095`。下载 APK 的 SHA-256：`0ecad6edfc29d3c8a3978ee6248edd0961919d0f7b41daa60f221d30d21e7ce6`。Manager main 与内核 builtin 分别固定，不能视为同一个源码提交。

## 内核和打包依赖

- LineageOS `lineage-24.0` 仍为 `98a7970af93b7e01ee77156e7fa0eb7e059a57f0`。
- SUSFS 稳定参考分支 `gki-android14-6.1` 仍为 `27e0a0e42745991ba09d6f96a97bf4b83f41a012`，本地 Linux 4.19 移植继续使用 v2.3.0。
- [builtin 更新](https://github.com/SukiSU-Ultra/SukiSU-Ultra/compare/ce75122bec7423e0f1fa06e3e9a174085c5231ab...0b666cad90f3a13cb4085f8c88e5144594e82030) 包含 priority UID 接口、版本伪装扩展、KPM 桥接及旧内核兼容修复。移除本地补丁中已由上游提供的重复改动，保留 Linux 4.19 SELinux hide 和动态 Manager 验证适配。KPM 仍按当前支持配置关闭。
- [AnyKernel3 更新](https://github.com/osm0sis/AnyKernel3/compare/020dfeccf9d7e962a48400fc94d3e451df92eead...08e9d1281f38019efcf8818e18525e55e679046f) 将 Magisk 工具更新至 v31.1 beta，并修复签名处理。打包工具变化需要重新核验安装包，旧产物的真机记录不能沿用。

## 本地验证

45 项本地回归通过。运行 `local-full-20261027-194856` 使用 builder `9623a65c7b68310ccfe98958bff47ea3e5cbc6e0`、16 任务并行，只编译 SUSFS `extended-full + SELinux hide` 一个 Image。源码、补丁、hook、配置和产物审计，以及 AnyKernel3 打包、导出校验全部通过。

本次复用既有对象工作区，重新编译 SukiSU 主对象并完成 ThinLTO 链接；make 为 120.819 秒，含同步和产物快照的增量步骤为 148.843 秒，流水线阶段合计 203.09 秒。流水线阶段时间不包含入口初始化和最终导出的全部耗时。

- Image SHA-256：`f33876485b3a6b5dddc3916e7af5a975d498d5d316af4074e4a1e4609d156a4b`
- 配置 SHA-256：`6d6f2b340e06861ae28ab2b7196c4c0ab9e9397cd0a1ee0e9a79e9501e448d25`
- System.map SHA-256：`b453dabdc13627c032bc92c847172086cc6b54adb3d5dcfc5c0436f5a57da4be`

本次尚未进行真机测试，也未发布版本。新候选使用自己的运行记录和哈希，不能沿用旧产物验收。

## 2026-10-28 发布补记

AnyKernel3 安装脚本修复后，维护者确认修复包的安装、启动及全部真机检查正常。本地验收核对原完整构建和修复包后通过，已发布 [v2026.10.28-ksu41095](https://github.com/Chinohana/oneplus-8t-kebab-sukisu-ultra-actions/releases/tag/v2026.10.28-ksu41095)。修复内容、包哈希及确认方式见[安装修复记录](INSTALLER-FIX-20261028.md)。
