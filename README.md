# OnePlus 8T · SukiSU Ultra + SUSFS

[![Checks](https://github.com/Chinohana/oneplus-8t-kebab-sukisu-ultra-actions/actions/workflows/control-tests.yml/badge.svg?branch=main)](https://github.com/Chinohana/oneplus-8t-kebab-sukisu-ultra-actions/actions/workflows/control-tests.yml)

为 OnePlus 8T 的 LineageOS 24.0 构建 SukiSU Ultra 内核，集成 SUSFS 和“隐藏 SELinux 修改”功能。基于 Linux 4.19，使用 SukiSU `builtin` 分支和 Inline Hook，关闭 KPM 与 kprobes。

[下载正式版本](https://github.com/Chinohana/oneplus-8t-kebab-sukisu-ultra-actions/releases/latest) · [下载与安装](#下载与安装) · [自行构建](docs/LOCAL-BUILD.md) · [历史移植记录](docs/README.md)

## 支持的设备与版本

| 项目 | 版本 |
| --- | --- |
| 设备 | OnePlus 8T（`kebab`，已测试型号 KB2000） |
| 系统 | LineageOS 24.0 / Android 17 / API 37 |
| 内核 | Linux 4.19，LineageOS `lineage-24.0` 分支 |
| Root | SukiSU Ultra `builtin`，41028 |
| SUSFS | v2.3.0，NON-GKI |
| 编译器 | Android Clang `r563880` |

当前正式发布为 [v2026.10.22-ksu41028](https://github.com/Chinohana/oneplus-8t-kebab-sukisu-ultra-actions/releases/tag/v2026.10.22-ksu41028)。本地编译、审计和交付校验已通过，具体测试覆盖见该版本说明。2026-10-18 的 LineageOS 24.0 真机批准属于此前的平台迁移记录，不代表后续每个构建都做过同样测试，详见 [24.0 迁移说明](docs/LINEAGE-24-EXPERIMENT.md)。

23.2 的最后版本保存在 [archive/lineage-23.2-final](https://github.com/Chinohana/oneplus-8t-kebab-sukisu-ultra-actions/tree/archive/lineage-23.2-final)，旧版测试记录也保留在对应文档中。

## 下载与安装

打开 [Releases](https://github.com/Chinohana/oneplus-8t-kebab-sukisu-ultra-actions/releases/latest)，在版本页的 **Assets** 中下载。正式包从本地构建后上传到这里，Actions 不再生成新内核包；其中的旧 artifact 只作历史资料，不作为当前版本下载入口。

| 文件 | 用途 |
| --- | --- |
| `…-AnyKernel3.zip` | 内核安装包，普通安装下载这个 |
| `SHA256SUMS` | 附件的 SHA-256 校验清单 |
| `…-full-artifacts.zip` | 完整交付归档，含内核包、配置、System.map、工具、日志和来源记录；不能直接刷入 |
| `Image` | 原始内核，供制作 boot 镜像使用，不是完整 boot 镜像 |
| `ksu_susfs-v2.3.0-arm64` | SUSFS 用户态工具，不是安装包 |

GitHub 自动附带的 **Source code (zip/tar.gz)** 是源码，不是可刷入的内核包。

### 校验下载

确认该版本适用于你的设备和 ROM，再将安装 ZIP 的 SHA-256 与同一版本的 `SHA256SUMS` 核对。Windows PowerShell 可用下面的命令，将示例文件名换成实际下载的文件名：

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath '.\你的内核包-AnyKernel3.zip'
```

### 安装与恢复

操作前解锁 Bootloader，备份 `boot_a`、`boot_b` 并保存哈希，确认能够通过 Fastboot 恢复。默认安装包是 AnyKernel3 ZIP，在支持该包的 Recovery 中刷入，具体兼容范围以版本说明为准。

1. 核对安装 ZIP 的机型、ROM 和哈希，记录当前活动槽位。
2. 在支持 AnyKernel3 的 Recovery 中安装该 ZIP，保留另一槽位用于恢复。
3. 开机后检查 root、SELinux Enforcing、SUSFS、存储解密、Wi-Fi、移动网络、相机、指纹、音频和文件读写。SELinux hide 需要时再手动开启。
4. 无法启动时进入 Fastboot，将原始 boot 备份写回原活动槽位；功能异常时保留 dmesg 和 pstore。

AnyKernel3 只替换 boot 内的内核，保留原有 ramdisk。需要先临时启动时，应基于当前 ROM 的原始 boot 制作测试 `boot.img`，再使用 `fastboot boot`。安装 ZIP、完整归档和原始 `Image` 都不能直接当作完整 boot 镜像；制作镜像时保留 ramdisk、DTB、DTBO、vendor_boot 和 init_boot。

## 包含的功能

默认使用 `extended-full`，包含 SUS Path、SUS Mount、SUS Kstat、SUS Maps、Spoof Uname、Spoof Cmdline / Bootconfig、Open Redirect、Hide KSU / SUSFS Symbols 和 SUSFS Logging。

SUSFS 自 v2.2 起移除了 Try Umount、自动添加挂载、Magic Mount 和 OverlayFS Auto Kstat，本项目沿用上游的功能范围。隐藏规则需要自行配置，首次启动时先保留空规则，再按需添加路径、映射、Kstat、重定向和伪装设置。

“隐藏 SELinux 修改”默认编译进内核，运行时需手动开启。开启后，应用 UID（≥10000）读取 `/sys/fs/selinux` 的 policy/status 时，会看到 KSU 规则注入前的策略；系统进程和 root 使用实时策略，SELinux 保持 Enforcing。该功能的既有真机测试和实现细节见[移植记录](docs/SELINUX-HIDE-EXPERIMENT.md)。

## 自行构建与维护

编译、配置矩阵、验收和发布准备全部在本地完成，GitHub 只保存代码并运行轻量检查。环境、参数、真机记录和发布工具见[本地构建说明](docs/LOCAL-BUILD.md)。维护者与 

普通安装直接使用上面的 Release 附件，无需搭建编译环境或运行 Actions。维护者上传正式版本时，保留完整来源记录，并在版本说明中写明实际完成的验证；完整矩阵和真机证据核验流程仍由本地工具提供。

## 已知问题

TA Enhanced v5.53.1 会停止 LineageOS 充电 HAL，导致软重启卡在启动阶段。移除模块中的停服务代码后，两次软重启通过，SELinux hide 保持开启。问题已报至 [TA Enhanced #46](https://github.com/Enginex0/tricky-addon-enhanced/issues/46)；模块更新可能覆盖手机上的临时修正。

早期日志中还有一次未定位的 memcg 警告和启用模块时的 Java 异常，记录见 [24.0 迁移说明](docs/LINEAGE-24-EXPERIMENT.md)。真机检查覆盖上面列出的项目，第三方模块和其他硬件组合仍需分别测试。

## 内核更新

仓库仍通过 Dependabot 检查 LineageOS `lineage-24.0` 提交并创建候选 PR。PR 的源码检查确认更新方向和目标分支，编译、验收和发布由本地工具完成。PR 检查通过不代表候选安装包已通过真机测试。

本地完整验收工具覆盖同一构建提交的四种配置：纯 SukiSU、SELinux hide、SUSFS `extended-stat`、`extended-full + SELinux hide`。本地验收还会核对完整配置包的 SHA-256、Image、配置、System.map、SUSFS 工具、阶段结果和真机记录。产物或构建输入变化后，旧测试记录不能用于新的候选。

这里跟进的是内核修复；LineageOS 月更中的 Android 系统、驱动二进制文件和应用层修复，仍需更新 ROM。

## 分支与移植文档

| 分支 | 用途 |
| --- | --- |
| [`main`](https://github.com/Chinohana/oneplus-8t-kebab-sukisu-ultra-actions/tree/main) | 默认构建完整 SUSFS，包含可选的 SELinux hide |
| [`SUSFS`](https://github.com/Chinohana/oneplus-8t-kebab-sukisu-ultra-actions/tree/SUSFS) | 不含 SELinux hide 的旧 main 快照 |
| [`legacy`](https://github.com/Chinohana/oneplus-8t-kebab-sukisu-ultra-actions/tree/legacy) | 不含 SUSFS 的旧版，固定在 `1bc3fb3` |

`experiment/susfs-v2.2-sm8250-4.19` 和 `experiment/selinux-hide-sm8250-4.19` 保留了早期移植过程。自行构建时，通过本地入口参数选择需要的功能。

24.0 的迁移和批准记录见 [迁移说明](docs/LINEAGE-24-EXPERIMENT.md)。41028 的同步和适配过程见 [2026-10-19 更新记录](docs/UPSTREAMS-20261019.md)，本次正式发布的验证范围以 Release 说明为准。固定提交、Linux 4.19 适配和历史测试记录见 [SUSFS 移植记录](docs/SUSFS-EXPERIMENT.md)、[SELinux hide 移植记录](docs/SELINUX-HIDE-EXPERIMENT.md)及[迁移起点的上游更新记录](docs/UPSTREAMS-20261017.md)。

## 上游项目

- [SukiSU Ultra](https://github.com/SukiSU-Ultra/SukiSU-Ultra)：使用支持传统 Manual Hook 的 `builtin` 分支。
- [SUSFS4KSU](https://gitlab.com/simonpunk/susfs4ksu)
- [AnyKernel3](https://github.com/osm0sis/AnyKernel3)
- [LineageOS OnePlus SM8250 kernel](https://github.com/LineageOS/android_kernel_oneplus_sm8250)
