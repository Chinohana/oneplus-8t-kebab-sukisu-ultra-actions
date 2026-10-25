# 2026-10-25 上游同步

本次将 SUSFS `gki-android14-6.1` 从 `c27ebe93c68e953c248b11bb747ef220ea648373` 更新到 `27e0a0e42745991ba09d6f96a97bf4b83f41a012`。版本仍为 v2.3.0。SukiSU builtin、LineageOS lineage-24.0、AnyKernel3 和工具链经核对保持原固定提交。

## Manager 与五位版本号

最新 Release 为 `v4.2.1-r2`，Manager 附件版本号为 41068。最新成功的 [Build Manager 运行 40107510955](https://github.com/SukiSU-Ultra/SukiSU-Ultra/actions/runs/40107510955) 对应 main 提交 `72eea67e2307cb9d257a4bbd8dd6e64f10724bc5`，实际附件为 `SukiSU_v4.2.1-r2_41074-release.apk`。该运行的 determine-version 日志记录 main 提交数 3889，按上游公式计算为 `40000 + 3889 - 2815 = 41074`。

[Release 到 Action 的差异](https://github.com/SukiSU-Ultra/SukiSU-Ultra/compare/v4.2.1-r2...72eea67e2307cb9d257a4bbd8dd6e64f10724bc5) 包含 6 个提交。其中 Manager 将主页、模块和 WebUI 工作移到后台，修复重新选择主页时的刷新和 SUSFS 配置空白处理，并将更新检查选项移到“关于”页面。按存在实质修复、功能或 UI 更新时选择 Action 的规则，本次驱动五位版本号固定为 **41074**。

驱动源码仍固定在 builtin `ce75122bec7423e0f1fa06e3e9a174085c5231ab`。Manager 的版本选择不改变驱动源码来源，也不代表已移植 main 的全部功能。

## SUSFS 4.19 移植

[两个新增提交](https://gitlab.com/simonpunk/susfs4ksu/-/compare/c27ebe93c68e953c248b11bb747ef220ea648373...27e0a0e42745991ba09d6f96a97bf4b83f41a012) 引入 priority UID filter，并同步内核和 KernelSU 集成补丁。此次变化涉及核心源码、头文件和用户态工具。

4.19 补丁更新 SUSFS 核心与接口定义，在 `getpriority`、`setpriority`、`ioprio_get` 和 `ioprio_set` 的按用户查询分支接入过滤。builtin 的 SUSFS 命令分发增加配置入口，包观察器在 SUSFS 开启时刷新应用 UID。原有 SELinux hide、Manager 验证和旧内核兼容处理继续保留。

新增宿主测试直接编译实际源码中的 UID 查询及包名校验函数，覆盖 10000–19999 全范围、多用户 UID 映射、相邻位隔离、空位图和包名路径校验。该测试已通过；完整内核编译和真机验证尚未完成。
