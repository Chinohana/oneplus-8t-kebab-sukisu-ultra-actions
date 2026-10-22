# OnePlus 8T · SukiSU Ultra + SUSFS

[![Build](https://github.com/Chinohana/oneplus-8t-kebab-sukisu-ultra-actions/actions/workflows/build-sukisu-ultra.yml/badge.svg?branch=main)](https://github.com/Chinohana/oneplus-8t-kebab-sukisu-ultra-actions/actions/workflows/build-sukisu-ultra.yml)

为 OnePlus 8T 的 LineageOS 24.0 构建 SukiSU Ultra 内核，集成 SUSFS 和“隐藏 SELinux 修改”功能。基于 Linux 4.19，使用 SukiSU `builtin` 分支和 Inline Hook，关闭 KPM 与 kprobes。

[构建内核](https://github.com/Chinohana/oneplus-8t-kebab-sukisu-ultra-actions/actions/workflows/build-sukisu-ultra.yml) · [SUSFS 移植记录](docs/SUSFS-EXPERIMENT.md) · [SELinux hide 移植记录](docs/SELINUX-HIDE-EXPERIMENT.md)

## 支持的设备与版本

| 项目 | 版本 |
| --- | --- |
| 设备 | OnePlus 8T（`kebab`，已测试型号 KB2000） |
| 系统 | LineageOS 24.0 / Android 17 / API 37 |
| 内核 | Linux 4.19，LineageOS `lineage-24.0` 分支 |
| Root | SukiSU Ultra `builtin`，41028 |
| SUSFS | v2.3.0，NON-GKI |
| 编译器 | Android Clang `r563880` |

LineageOS 24.0 版本已于 2026-10-18 完成真机批准并合入主线。四种云端配置均构建通过，已核对手机内核与批准产物的哈希，以及 root、SELinux Enforcing、SUSFS、隐藏开关、存储解密、连接状态和前后相机预览。详细记录见 [24.0 迁移说明](docs/LINEAGE-24-EXPERIMENT.md)。

23.2 的最后版本保存在 [archive/lineage-23.2-final](https://github.com/Chinohana/oneplus-8t-kebab-sukisu-ultra-actions/tree/archive/lineage-23.2-final)，旧版测试记录也保留在对应文档中。

## 包含的功能

默认使用 `extended-full`，包含 SUS Path、SUS Mount、SUS Kstat、SUS Maps、Spoof Uname、Spoof Cmdline / Bootconfig、Open Redirect、Hide KSU / SUSFS Symbols 和 SUSFS Logging。

SUSFS 自 v2.2 起移除了 Try Umount、自动添加挂载、Magic Mount 和 OverlayFS Auto Kstat，本项目沿用上游的功能范围。隐藏规则需要自行配置，首次启动时先保留空规则，再按需添加路径、映射、Kstat、重定向和伪装设置。

“隐藏 SELinux 修改”默认编译进内核，运行时需手动开启。开启后，应用 UID（≥10000）读取 `/sys/fs/selinux` 的 policy/status 时，会看到 KSU 规则注入前的策略；系统进程和 root 使用实时策略，SELinux 保持 Enforcing。该功能的既有真机测试和实现细节见[移植记录](docs/SELINUX-HIDE-EXPERIMENT.md)。

## 构建

本地与 Actions 共用构建阶段。日常试编译使用 E 盘 `OnePlus8T-Build` 中的专用 WSL；首次使用先看[本地构建说明](docs/LOCAL-BUILD.md)，运行只读预检，再启动编译。正式采纳仍需云端矩阵复核和真机审批。以下为云端入口。

进入 [Actions](https://github.com/Chinohana/oneplus-8t-kebab-sukisu-ultra-actions/actions)，选择 **Build kebab SukiSU Ultra**，点击 **Run workflow**。默认构建完整 SUSFS、SELinux hide 和 AnyKernel3 ZIP，并开启 ccache。

| 选项 | 用途 |
| --- | --- |
| `Enable SUSFS` | 编译 SUSFS；关闭后构建纯 SukiSU 内核 |
| `SUSFS profile` | 选择 SUSFS 功能配置，见下表 |
| `Enable SELinux hide` | 编译“隐藏 SELinux 修改”，可独立于 SUSFS 开关 |
| `Use AnyKernel3` | 打包为 ZIP；关闭后输出 `Image`、`System.map`、配置和构建来源记录（provenance） |
| `Use ccache` | 缓存编译输出，加快重复构建 |
| `Kernel source` | `approved-pin` 使用已批准的内核提交；`latest-lineage-24.0` 使用运行时获取的上游最新提交 |

| SUSFS 配置 | 功能 |
| --- | --- |
| `smoke` | SUSFS 核心与日志 |
| `minimal-mount` | `smoke` + SUS Mount |
| `extended-stat` | `minimal-mount` + SUS Kstat |
| `extended-full` | 上述九项功能，默认配置 |

关闭 SUSFS 后，`SUSFS profile` 不生效。新配置首次构建约需 75–90 分钟，缓存建立后，同样输入的重复构建预计约需 30–45 分钟。

构建成功后，在该次运行页面下载 kernel artifact，核对其中的 SHA-256 和 provenance。构建会检查源码版本、补丁、内核配置、符号、编译警告和 Image 大小。

选择最新内核源码时，产物以 `UNAPPROVED_LATEST_` 开头，保留 30 天；SukiSU、SUSFS、编译器和打包工具仍使用各自的固定版本。该选项仅影响本次构建，正式构建的内核提交通过下述更新流程调整。

## 安装与恢复

刷入错误的内核可能导致无法开机或数据丢失。操作前需解锁 Bootloader，备份 `boot_a`、`boot_b` 并记录 SHA-256，确认自己能通过 Fastboot 恢复。

默认产物是 AnyKernel3 ZIP。包内使用 `split_boot` / `flash_boot`，只替换 boot 中的内核 `Image`，保留原有 ramdisk。若要制作临时启动镜像，应从当前 ROM 的原始 boot 镜像中替换 `Image`，保留 ramdisk、DTB、DTBO、`vendor_boot` 和 `init_boot`。

1. 确认当前活动槽位，用 `fastboot boot` 临时启动测试镜像。
2. 检查开机、ADB、root、加密存储、SELinux Enforcing，以及 Wi-Fi、移动网络、相机、指纹、音频和文件读写。
3. 检查 SUSFS、SELinux hide 开关和 dmesg、pstore，确认没有 panic、oops、BUG、UAF 或 lockup。
4. 测试通过后，再写入当前活动槽位，保留另一槽位用于恢复。

如果无法开机，进入 Fastboot，将备份的原始 boot 镜像写回原活动槽位。功能异常或内核报错时，保存 dmesg 和 pstore，便于排查。

## 已知问题

TA Enhanced v5.53.1 会停止 LineageOS 充电 HAL，导致软重启卡在启动阶段。移除模块中的停服务代码后，两次软重启通过，SELinux hide 保持开启。问题已报至 [TA Enhanced #46](https://github.com/Enginex0/tricky-addon-enhanced/issues/46)；模块更新可能覆盖手机上的临时修正。

早期日志中还有一次未定位的 memcg 警告和启用模块时的 Java 异常，记录见 [24.0 迁移说明](docs/LINEAGE-24-EXPERIMENT.md)。真机检查覆盖上面列出的项目，第三方模块和其他硬件组合仍需分别测试。

## 内核更新

仓库每天检查 LineageOS `lineage-24.0` 的新提交，并创建候选 PR。候选包以 `CANDIDATE_` 开头，保留 30 天。CI 会编译纯 SukiSU、SELinux hide、SUSFS `extended-stat` 和 `extended-full + SELinux hide` 四种组合；构建失败会记录到 `Kernel update blocked: lineage-24.0` Issue。

采用候选版本前，先核对包的 SHA-256，按上面的步骤完成真机测试，再运行 **Approve kernel candidate** 并勾选真机测试确认项。工作流会定位唯一开放且构建成功的候选 PR，核验构建指纹和 ZIP 哈希，保存审批记录，最后由人工审核合并。

审批对应具体的候选内容。内核、补丁、工具版本或构建脚本变化后，需要重新构建和测试。首次迁移审批流程时，只有 `Image`、配置和 `System.map` 均与旧批准构建相同，才能沿用旧真机结果。

这里跟进的是内核修复；LineageOS 月更中的 Android 系统、驱动二进制文件和应用层修复，仍需更新 ROM。

## 分支与移植文档

| 分支 | 用途 |
| --- | --- |
| [`main`](https://github.com/Chinohana/oneplus-8t-kebab-sukisu-ultra-actions/tree/main) | 默认构建完整 SUSFS，包含可选的 SELinux hide |
| [`SUSFS`](https://github.com/Chinohana/oneplus-8t-kebab-sukisu-ultra-actions/tree/SUSFS) | 不含 SELinux hide 的旧 main 快照 |
| [`legacy`](https://github.com/Chinohana/oneplus-8t-kebab-sukisu-ultra-actions/tree/legacy) | 不含 SUSFS 的旧版，固定在 `1bc3fb3` |

`experiment/susfs-v2.2-sm8250-4.19` 和 `experiment/selinux-hide-sm8250-4.19` 保留了早期移植过程。构建当前版本时，也可以直接在工作流中关闭不需要的功能。

24.0 的迁移和批准记录见 [迁移说明](docs/LINEAGE-24-EXPERIMENT.md)。41028 依赖同步仍为待重新构建、真机测试及批准的候选，见 [2026-10-19 更新记录](docs/UPSTREAMS-20261019.md)。固定提交、Linux 4.19 适配和历史测试记录见 [SUSFS 移植记录](docs/SUSFS-EXPERIMENT.md)、[SELinux hide 移植记录](docs/SELINUX-HIDE-EXPERIMENT.md)及[迁移起点的上游更新记录](docs/UPSTREAMS-20261017.md)。

## 上游项目

- [SukiSU Ultra](https://github.com/SukiSU-Ultra/SukiSU-Ultra)：使用支持传统 Manual Hook 的 `builtin` 分支。
- [SUSFS4KSU](https://gitlab.com/simonpunk/susfs4ksu)
- [AnyKernel3](https://github.com/osm0sis/AnyKernel3)
- [LineageOS OnePlus SM8250 kernel](https://github.com/LineageOS/android_kernel_oneplus_sm8250)
