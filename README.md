# OnePlus 8T SukiSU Ultra + SUSFS v2.2

[![Build](https://github.com/Chinohana/oneplus-8t-kebab-sukisu-ultra-actions/actions/workflows/build-sukisu-ultra.yml/badge.svg?branch=main)](https://github.com/Chinohana/oneplus-8t-kebab-sukisu-ultra-actions/actions/workflows/build-sukisu-ultra.yml)

这是一个为 OnePlus 8T（`kebab` / KB2000）制作的内核构建项目。它在固定的
LineageOS 23.2 Linux 4.19 内核上集成了 SukiSU Ultra 和 SUSFS v2.2。

> [!CAUTION]
> 这个项目只适用于下方列出的设备和系统版本，目前仍是测试版本。刷入错误的
> 内核可能导致无法开机或数据丢失。请先备份原始 boot 镜像，并确保你能使用
> Fastboot 恢复。不要把这里的产物用于其他手机、其他 ROM 或其他内核版本。

## 适用范围

| 项目 | 要求 |
| --- | --- |
| 设备 | OnePlus 8T（`kebab`，已测试型号 KB2000） |
| 系统 | LineageOS 23.2 / Android 16 |
| 内核 | Linux 4.19，LineageOS `lineage-23.2` 分支；确切提交见内核书签 |
| Root | SukiSU Ultra `builtin`，版本 40856 |
| SUSFS | v2.2.0，NON-GKI，Inline Hook |
| 编译器 | Android Clang `r563880` |

不满足这些条件时，请不要使用本项目产物。

## 当前状态

`main` 默认构建 `extended-full`，也就是当前已经在开发设备上启动并安装过的
完整 SUSFS 配置。

已经完成的检查包括：

- GitHub Actions 完整编译与配置审计；
- 使用 `fastboot boot` 临时启动；
- 将同一个已测试镜像写入当前活动的 `boot_b`；
- SukiSU root、ADB、SELinux Enforcing 和加密存储正常；
- Wi-Fi、移动网络、相机、指纹、音频和文件读写正常；
- `susfs4ksu v2.2.0-R28` 正常启动，sdcard 监控正常；
- pstore 为空，未发现 panic、oops、BUG、UAF 或 lockup。

尚未完成长期稳定性观察和大量重复冷启动测试，因此这里的“可用”不代表已经达到
生产级稳定性。

## SUSFS 功能

`extended-full` 包含当前官方 SUSFS v2.2 提供的九项功能：

- SUS Path
- SUS Mount
- SUS Kstat
- SUS Maps
- Spoof Uname
- Spoof Cmdline / Bootconfig
- Open Redirect
- Hide KSU / SUSFS Symbols
- SUSFS Logging

旧版 Try Umount、自动添加挂载、Magic Mount 和 OverlayFS Auto Kstat 已被
SUSFS v2.2 废弃，因此没有重新加入。KPM 和 kprobes 也保持关闭。

编译进内核不等于自动创建隐藏规则。首次启动时应保持自定义路径、映射、Kstat、
重定向和伪装设置为空，再按需逐项配置。

## 分支说明

| 分支 | 用途 |
| --- | --- |
| [`main`](https://github.com/Chinohana/oneplus-8t-kebab-sukisu-ultra-actions/tree/main) | SUSFS v2.2 完整版 + 可选的“隐藏 SELinux 修改”功能 |
| [`SUSFS`](https://github.com/Chinohana/oneplus-8t-kebab-sukisu-ultra-actions/tree/SUSFS) | 仅 SUSFS v2.2 完整版，不含 SELinux 隐藏（旧 main 快照） |
| [`legacy`](https://github.com/Chinohana/oneplus-8t-kebab-sukisu-ultra-actions/tree/legacy) | 不含 SUSFS 的旧版 SukiSU 内核，固定在 `1bc3fb3` |
| `experiment/susfs-v2.2-sm8250-4.19` | SUSFS 移植过程的历史开发分支 |
| `experiment/selinux-hide-sm8250-4.19` | “隐藏 SELinux 修改”移植的历史实验分支 |

只想使用原来的无 SUSFS 版本时，请切换到 `legacy`。
只想使用无 SELinux 隐藏的 SUSFS 版本时，请切换到 `SUSFS`。

## 隐藏 SELinux 修改（默认包含）

`main` 已包含 SukiSU“隐藏 SELinux 修改”的 Linux 4.19 回移植。该功能是可选
开关：默认编译进内核，但不会自动启用，也不会把 SELinux 切换为 Permissive。它让应用
UID（≥10000）读取 `/sys/fs/selinux` 的 policy/status 时看到的是 KSU 规则注入
前的干净策略，系统进程与 root 仍使用实时策略。

该功能已在开发机（OnePlus 8T / LineageOS 23.2）上完成真机复验：三轮以上
冷启动、应用正常启动、无崩溃循环、开关往返正常、pstore 为空。实现边界、
构建标识和验证记录见
[`docs/SELINUX-HIDE-EXPERIMENT.md`](docs/SELINUX-HIDE-EXPERIMENT.md)。

不需要该功能时，构建时关闭 **Enable SELinux hide** 选项即可。

## 云端构建

1. 打开仓库的 [Actions](https://github.com/Chinohana/oneplus-8t-kebab-sukisu-ultra-actions/actions) 页面。
2. 选择 **Build kebab SukiSU Ultra**。
3. 点击 **Run workflow**。
4. 按需选择选项（默认全部开启）：
   - **Enable SUSFS**：编译 SUSFS v2.2；关闭时产物为纯 SukiSU builtin 内核。
   - **SUSFS profile**：SUSFS 功能档位（见下表），仅在 Enable SUSFS 开启时生效。
   - **Enable SELinux hide**：编译“隐藏 SELinux 修改”（Linux 4.19 回移植）。
   - **Use AnyKernel3**：打包为 AnyKernel3 ZIP；关闭时产物为 raw
     `Image` / `System.map` / 配置与 provenance。
   - **Use ccache**：用 ccache 缓存编译输出（默认开启）。同 pin 的重复
     构建会直接命中缓存，把单次构建从约 75 分钟降到约 15–20 分钟；新
     pin 首次构建约 45 分钟。产物与审计结果不受影响（ccache 对相同输入
     重放完全相同的编译输出）。关闭后回到不带缓存的旧构建路径。
5. 构建成功后下载 kernel artifact，并核对其中的 SHA-256 和 provenance。

手动正式构建永远使用仓库已经批准的固定版本，不能临时追踪上游。内核、
SukiSU、SUSFS、编译器和打包工具分别固定；更新内核不会顺带更新其他项目。

工作流提供四种配置：

| 配置 | 内容 | 状态 |
| --- | --- | --- |
| `smoke` | SUSFS 核心与日志 | 已真机验证 |
| `minimal-mount` | `smoke` + SUS Mount | 已真机验证 |
| `extended-stat` | `minimal-mount` + SUS Kstat | 仅完成编译审计 |
| `extended-full` | 九项官方 v2.2 功能 | 默认；已安装并启动验证 |

关闭 **Enable SUSFS** 时，`SUSFS profile` 被忽略，产物不含 SUSFS；SUSFS 与
SELinux hide 可自由组合（四个组合均受 CI 审计）。

每次构建都会重新检查固定源码版本、补丁落点、最终内核配置、符号、编译警告和
Image 大小。内核、SukiSU、SUSFS、Clang 和 AnyKernel3 都使用固定提交，避免
上游更新悄悄改变结果。

## 内核安全更新怎样进入本仓库

仓库每天检查一次 LineageOS `lineage-23.2` 内核分支。发现新提交时，只会创建
一个候选 PR，不会自动合并、刷机或替换正式内核。

候选 PR 会先确认新提交确实是该分支的最新提交，而且位于旧提交之后。云端随后
编译纯 SukiSU、SELinux hide、SUSFS `extended-stat` 和当前使用的
`extended-full + SELinux hide`，并重复配置、符号、补丁及 Image 大小检查。
测试包名称以 `CANDIDATE_` 开头，保存 30 天。编译失败时，仓库会打开或更新
`Kernel update blocked: lineage-23.2` Issue，防止更新悄悄卡住。

云端通过不等于可以采用。下载当前配置的候选包后，按以下顺序在 OnePlus 8T
上测试：

1. 核对候选页面给出的 SHA-256；
2. 先用 `fastboot boot` 临时启动，不要直接刷入；
3. 检查开机、ADB、root、加密存储、SELinux Enforcing 和主要硬件；
4. 检查 SUSFS，并来回开关一次 SELinux hide；
5. 确认 dmesg 与 pstore 没有 panic、oops、BUG、UAF 或 lockup；
6. 测试完全通过后，手动运行 **Approve kernel candidate**，填写 PR 编号、
   构建指纹、已测试包 SHA-256 和手机当前 ROM build fingerprint。

批准记录只对那个 PR 的那次内容有效。内核、补丁、工具版本或构建脚本中任何
一项改变，都必须重新编译并重新真机测试。最终仍需要人工审核并点击合并。

首次迁移新流程时也会比较旧批准构建的 `Image`、配置和 `System.map`。三项完全
相同才能沿用旧真机结果；只要一项不同，就和普通内核更新一样重新真机测试。

> [!IMPORTANT]
> 跟随内核仓库只能取得内核里的修复。LineageOS 月更还可能包含 Android 系统、
> 驱动二进制文件和应用层修复；更新内核不代表已经包含整个月度安全更新。

## 固定的其他上游项目

- **SukiSU**：`builtin` 分支是支持传统 Manual Hook（非 GKI 内联调用、
  无需 KPROBES）的分支，本仓库固定其最新提交 `b1d534bc`。SukiSU 的
  `main` 分支（v4.x）是新一代架构，`CONFIG_KSU` 硬依赖 `CONFIG_KPROBES`
  且使用运行时 syscall 打补丁与 LSM Hook，与本项目"KPM/kprobes 关闭、
  禁止运行时打补丁"的约束冲突，因此不用于本仓库。

本仓库目前只支持 LineageOS 23.2，不为 LineageOS 24.0 产出正式包。将来手机
正式升级到 24.0 后，会建立一套新的内核书签并重新完成首次真机批准。

## 安装前必须知道

Actions 产物是 AnyKernel3 ZIP，不是与你当前 ROM 完全匹配的独立 `boot.img`。
为了避免混入错误的 ramdisk 或 DTB，本项目不会自动读取、修改或刷写手机。

推荐的安全流程是：

1. 确认 Bootloader 已解锁，并检查当前活动槽位；
2. 分别备份 `boot_a` 和 `boot_b`，记录 SHA-256；
3. 只替换当前原始 boot 镜像里的内核 `Image`，不要修改 ramdisk、DTB、DTBO、
   `vendor_boot` 或 `init_boot`；
4. 先使用 `fastboot boot` 临时启动测试；
5. 确认系统、root、存储和主要硬件正常后，才考虑写入当前活动槽位；
6. 不要自动切槽，也不要同时覆盖两个 boot 槽位。

如果你不熟悉 boot 镜像拆包、Fastboot 临时启动和恢复流程，请不要直接刷写。

## 出现问题时

遇到无法开机、功能异常或内核报错时：

1. 停止继续测试，不要反复刷写；
2. 进入 Fastboot；
3. 将事先备份的原始 boot 镜像写回原活动槽位；
4. 保持另一槽位不变；
5. 保存 dmesg 和 pstore，便于定位问题。

仓库不会自动刷机、自动切换槽位或创建 Release。

## 给开发者

详细的固定提交、Linux 4.19 适配点、CI 阻断条件和真机验证记录见
[`docs/SUSFS-EXPERIMENT.md`](docs/SUSFS-EXPERIMENT.md)。

主要上游项目：

- [SukiSU Ultra](https://github.com/SukiSU-Ultra/SukiSU-Ultra)
- [SUSFS4KSU](https://gitlab.com/simonpunk/susfs4ksu)
- [AnyKernel3](https://github.com/osm0sis/AnyKernel3)
- [LineageOS OnePlus SM8250 kernel](https://github.com/LineageOS/android_kernel_oneplus_sm8250)
