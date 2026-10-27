# OnePlus 8T · SukiSU Ultra + SUSFS

[![Checks](https://github.com/Chinohana/oneplus-8t-kebab-sukisu-ultra-actions/actions/workflows/control-tests.yml/badge.svg?branch=main)](https://github.com/Chinohana/oneplus-8t-kebab-sukisu-ultra-actions/actions/workflows/control-tests.yml)

为 OnePlus 8T 的 LineageOS 24.0 构建 SukiSU Ultra 内核，基于 Linux 4.19 和 SukiSU `builtin`。维护者只编译和提供完整功能版：SUSFS `extended-full`、SELinux hide 和 AnyKernel3 安装包。

[下载正式版本](https://github.com/Chinohana/oneplus-8t-kebab-sukisu-ultra-actions/releases/latest) · [下载与安装](#下载与安装) · [自定义构建](docs/CUSTOM-BUILD.md) · [本地构建与发布](docs/LOCAL-BUILD.md)

## 支持范围与版本

| 项目 | 版本 |
| --- | --- |
| 设备 | OnePlus 8T（`kebab`，已测试型号 KB2000） |
| 系统 | LineageOS 24.0 / Android 17 / API 37 |
| 内核 | Linux 4.19，LineageOS `lineage-24.0` |
| 当前源码固定版本 | SukiSU builtin 41074、SUSFS v2.3.0 NON-GKI |
| 最新正式发布 | [v2026.10.24-ksu41057](https://github.com/Chinohana/oneplus-8t-kebab-sukisu-ultra-actions/releases/tag/v2026.10.24-ksu41057) |
| 编译器 | Android Clang `r563880` |

41057 已完成当时的本地矩阵与真机验收，见 [2026-10-24 记录](docs/UPSTREAMS-20261024.md)。10 月 25 日的 41074 候选已完成本地构建、审计和交付校验，尚未完成该候选的真机验收；源码版本不等于已发布版本。上游更新与 Manager 版本选择见 [2026-10-25 记录](docs/UPSTREAMS-20261025.md)。

## 下载与安装

在 [Releases 的 Assets](https://github.com/Chinohana/oneplus-8t-kebab-sukisu-ultra-actions/releases/latest) 下载适合设备和 ROM 的文件。此后维护者发布的内核只提供完整功能版，不再分别提供精简版或关闭 SELinux hide 的安装包。既有历史附件保留原样。

当前正式版可直接下载：[内核安装 ZIP](https://github.com/Chinohana/oneplus-8t-kebab-sukisu-ultra-actions/releases/download/v2026.10.24-ksu41057/SukiSU-kebab-LOS24.0-KSU41057-20261024-AnyKernel3.zip) · [SHA256SUMS](https://github.com/Chinohana/oneplus-8t-kebab-sukisu-ultra-actions/releases/download/v2026.10.24-ksu41057/SHA256SUMS)。

| 文件 | 用途 |
| --- | --- |
| `…-AnyKernel3.zip` | 可安装的内核 ZIP |
| `SHA256SUMS` | 同版本附件的哈希清单 |
| `…-full-artifacts.zip` | 配置、工具与来源记录等完整交付归档，不能直接刷入 |
| `Image` | 原始内核，不是完整 boot 镜像 |
| `ksu_susfs-v2.3.0-arm64` | SUSFS 用户态工具 |

GitHub 自动附带的 **Source code (zip/tar.gz)** 是源码。Manager APK 按对应版本的说明获取，五位版本号应与内核匹配。

在 PowerShell 核对安装 ZIP 的 SHA-256，与同一 Release 的清单比较：

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath '.\你的内核包-AnyKernel3.zip'
```

操作前解锁 Bootloader，备份 `boot_a`、`boot_b` 并保存哈希，记录活动槽位和 Fastboot 恢复方法。

1. 确认设备、ROM 和安装包哈希，在支持 AnyKernel3 的 Recovery 中安装 ZIP，保留另一槽位用于恢复。
2. 开机后检查 root、SELinux Enforcing、SUSFS、存储解密、网络、相机、指纹、音频和文件读写。SELinux hide 需要时再手动开启。
3. 无法开机时，通过 Fastboot 将原始 boot 备份写回原活动槽位；出现异常时保留 dmesg 和 pstore。

需要先临时启动时，从当前 ROM 原始 boot 中替换内核 `Image`，制作测试 `boot.img` 后使用 `fastboot boot`。AnyKernel3 只替换 boot 内核并保留 ramdisk；安装 ZIP、交付归档和原始 Image 都不能直接当作完整 boot 镜像。保留原有 DTB、DTBO、vendor_boot 和 init_boot。

## 完整功能版

完整功能版包含 SUS Path、SUS Mount、SUS Kstat、SUS Maps、Spoof Uname、Spoof Cmdline / Bootconfig、Open Redirect、Hide KSU / SUSFS Symbols、SUSFS Logging、priority UID filter，以及 SELinux hide 支持。

“全部启用”指本项目已适配功能均编译进内核。隐藏规则、UID 过滤名单和 SELinux hide 等运行时开关仍由使用者配置，首次启动保留空规则。KPM 与 kprobes 不属于当前 4.19 适配范围，继续关闭。SUSFS 上游已移除的 Try Umount、Magic Mount 等功能不会补回。

SELinux hide 开启后，应用 UID（≥10000）读取 `/sys/fs/selinux` 的 policy/status 时使用 KSU 规则注入前的策略；系统进程和 root 使用实时策略，SELinux 保持 Enforcing。实现与既有测试见[移植记录](docs/SELINUX-HIDE-EXPERIMENT.md)。

## 自定义构建与维护

需要关闭 SUSFS、关闭 SELinux hide 或选择其他 SUSFS 配置时，可以克隆项目后推送到自己的 GitHub 仓库，或直接 Fork，然后运行 **Build kebab SukiSU Ultra** 的 GitHub Actions。每次只构建所选的一个配置，步骤见[自定义构建](docs/CUSTOM-BUILD.md)。仅将源码克隆到本地不会获得 GitHub Actions 入口。

维护者继续在本地构建、验收和准备发布。默认命令只编译 `extended-full + SELinux hide` 的一个 Image，不再附带基线、smoke、minimal-mount 或四组合矩阵编译。正式发布核对该完整配置产物的哈希、审计结果及实际真机记录，见[本地操作手册](docs/LOCAL-BUILD.md)。

主仓库的手动构建工作流只显示本地维护入口；自定义编译仅在使用者自己的仓库运行，不自动创建 Release。PR 的轻量检查不代表内核产物或真机验收通过。

## 已知问题

TA Enhanced v5.53.1 会停止 LineageOS 充电 HAL，导致软重启卡在启动阶段。移除模块中的停服务代码后，两次软重启通过，SELinux hide 保持开启。问题见 [TA Enhanced #46](https://github.com/Enginex0/tricky-addon-enhanced/issues/46)；模块更新可能覆盖临时修正。

早期 memcg 警告、Java 异常和历史硬件检查见 [24.0 迁移说明](docs/LINEAGE-24-EXPERIMENT.md)。第三方模块与其他硬件组合需要分别验证。

## 内核更新与历史资料

Dependabot 继续检查 LineageOS `lineage-24.0` 并创建候选 PR。源码检查通过后，在本地构建完整功能版；产物或输入变化后，旧真机记录不能用于新候选。Android 系统、驱动二进制文件和应用层修复仍需更新 ROM。

23.2 的最后版本保存在 [archive/lineage-23.2-final](https://github.com/Chinohana/oneplus-8t-kebab-sukisu-ultra-actions/tree/archive/lineage-23.2-final)。`SUSFS`、`legacy` 及实验分支用于追溯，不作为当前默认下载入口。[文档目录](docs/README.md) 区分现行手册与历史记录；历史四组合测试不再是新构建的要求。

## 上游项目

- [SukiSU Ultra](https://github.com/SukiSU-Ultra/SukiSU-Ultra)：使用 `builtin` 分支。
- [SUSFS4KSU](https://gitlab.com/simonpunk/susfs4ksu)
- [AnyKernel3](https://github.com/osm0sis/AnyKernel3)
- [LineageOS OnePlus SM8250 kernel](https://github.com/LineageOS/android_kernel_oneplus_sm8250)
