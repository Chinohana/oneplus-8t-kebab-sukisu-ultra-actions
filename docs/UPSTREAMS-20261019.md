# 2026-10-19 上游同步候选

本文是历史移植和验证记录。当前编译、验收和发布全部在本地执行，操作入口见[本地构建说明](LOCAL-BUILD.md)；下文保留的云端步骤只用于追溯。

这次更新同步 SukiSU `builtin` 与 SUSFS 的固定提交，保留 Linux 4.19、LineageOS 24.0 和现有工具链。候选版本需要重新通过四种云端构建及真机测试；2026-10-18 的批准记录只对应此前的依赖组合。

| 输入 | 本次核对结果 |
| --- | --- |
| LineageOS `lineage-24.0` | 上游仍为 `98a7970af93b7e01ee77156e7fa0eb7e059a57f0`，不变 |
| SukiSU `builtin` | `0af2cf9cef7dc2239fa7ebb3f7898830a1087e26` → `5ef32ad5d5eba3033f86467fd4fa094e032c5237` |
| SukiSU 驱动版本 | 41001 → 41028；按 Manager 构建提交 `ad8b30d60ca706080d08307728dedbe9cf944a7e` 的 main 历史计数 3843，沿用上游公式 `40000 + 3843 - 2815` |
| SUSFS `gki-android14-6.1` | `5369359dbd10f6dd8cbdd59d1df7b788b29b168c` → `f6c046775c0a14834748cc82c03f1d1b0285c206`，仍为 v2.3.0 |
| AnyKernel3 | 上游 HEAD 仍为 `020dfeccf9d7e962a48400fc94d3e451df92eead`，不变 |
| SM8250 移植参考 | 保留 `ac5f7e57d3f1d4ed065940960d7348c8baae3fb9`；这是补丁落点记录，不跟随参考仓库 HEAD |
| 编译器与 NDK | 按本次要求排除更新：Clang `r563880`、归档提交 `6f88d37dd82ba741ca279539d44bb7da27ab1844`、NDK `27.2.12479018` 均不变 |

## SukiSU 兼容调整

新 `builtin` 使用 UAPI 6，并将动态 Manager 等接口迁入 extension 子系统。构建检查改为验证 extension ioctl、分发函数和动态 Manager 实现，不再补回旧 ioctl 106 或将 UAPI 降回 5。上游已修正 observer 的同步扫描调用，因此删除对应的重复补丁。

Manager 扫描仍需本地修正：先解析当前 APK 包名，内置分支仅匹配内置包名，动态分支仅检查当前包，再验证注册 UID 和证书。保留十项授权回归测试，并在云端的 baseline、experiment 两棵源码树上分别执行。

两份 SukiSU 补丁重基到新源码。Linux 4.19 的 SELinux 状态备份、假状态页生命周期及重启后启用逻辑保留；新 extension 初始化和强制配置调用也保留。

云端首次编译发现两处新增扩展的旧内核适配缺口：CPU spoof 使用的 `clocksource.vdso_clock_mode` 在本内核中对应 `archdata.vdso_direct`；KPM 的三份底层实现未受配置保护，即使关闭 KPM 也会编译。兼容补丁分别适配旧字段，并让底层 KPM 代码仅在 `CONFIG_KPM` 开启时编译，extension 的“不支持”查询路径继续保留。

上游新增 `mount_hide` 默认启用，通过文件打开钩子拒绝目标应用读取挂载信息。其文件分类器原先仅检查文件名，本次增加 `PROC_SUPER_MAGIC` 检查，避免拦截 ext4、tmpfs 等文件系统中的同名文件。新增宿主测试直接编译实际分类器，覆盖 procfs 的三个目标名、普通文件系统同名文件、非目标名和空输入。此功能的应用兼容性仍需真机检查。

## SUSFS 集成补丁

稳定分支新增四个提交：重基到 Android 14 的 6.1.176、继续修复 SELinux hide、同步 KernelSU，以及复用上游 SELinux 查询函数。官方比较结果只修改两份集成补丁，`fs/susfs.c`、两份头文件和 userspace 工具源码未变。

拉取固定 SUSFS 提交增加最多三次重试，处理本次遇到的 GitLab 临时负载错误；最终仍严格校验取回的提交。

本项目的 4.19 补丁已在 context/access 查询中选择备份状态，status-open 也优先使用已有假页，因此保留这些独立的旧内核实现。GKI 集成补丁中的 preinit 和现代 SELinux 接口不直接套用到 4.19。

## 验证与采用

本地执行严格补丁应用检查、十项 Manager 授权测试、挂载分类器测试及九项平台审批测试。完整编译由 PR 的 `Kernel candidate` 工作流执行，覆盖纯 SukiSU、SELinux hide、SUSFS extended-stat 和 extended-full + hide。构建成功后仍须对候选产物进行真机测试，并通过既有审批工作流；本次同步不沿用旧产物的批准。

上游依据：[SukiSU 提交](https://github.com/SukiSU-Ultra/SukiSU-Ultra/commit/5ef32ad5d5eba3033f86467fd4fa094e032c5237)、[Manager 构建](https://github.com/SukiSU-Ultra/SukiSU-Ultra/actions/runs/39260333691)、[SUSFS 提交](https://gitlab.com/simonpunk/susfs4ksu/-/commit/f6c046775c0a14834748cc82c03f1d1b0285c206)。
