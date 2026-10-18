# SUSFS 的 Linux 4.19 移植记录

本项目在 OnePlus 8T 的 Linux 4.19 内核上集成 NON-GKI SUSFS。当前主线使用 v2.3 / SukiSU 41001；本文记录移植方案和早期 v2.2 真机测试，24.0 的批准结果见[迁移记录](LINEAGE-24-EXPERIMENT.md)。

无 SUSFS 的原始基线保存在 `legacy@1bc3fb3`，早期移植过程保存在 `experiment/susfs-v2.2-sm8250-4.19`。

## 源码与补丁基线

| 输入 | 移植记录中的版本 |
| --- | --- |
| LineageOS 内核 | `98a7970af93b7e01ee77156e7fa0eb7e059a57f0`，最初来自 `lineage-23.2` |
| SukiSU `builtin` | `0af2cf9cef7dc2239fa7ebb3f7898830a1087e26`，41001 |
| SUSFS v2.3 | `5369359dbd10f6dd8cbdd59d1df7b788b29b168c` |
| SM8250 v2.1 补丁落点参考 | `ac5f7e57d3f1d4ed065940960d7348c8baae3fb9` |
| Clang | `r563880` |
| 内核配置 | `vendor/kona-perf_defconfig + vendor/oplus.config` |

当前构建输入由 `config/build-pins.env` 和其中指定的内核 gitlink 管理。v2.1 参考只用于确认补丁落点，其 KernelSU-Next、`drivers/kernelsu`、KPM、input hook、defconfig 和第三方 root 改动未纳入本移植。

SukiSU 4.2 兼容补丁将 no-su 与 zygote_next 进程标记分开，并保护 zygote_next 的挂载查找。41001 的 Manager 授权修复见[上游更新记录](UPSTREAMS-20261017.md)。

## v2.2 的 4.19 适配

移植保留官方头文件和命令 ABI，改动集中在旧内核接口：

- 使用 Linux 4.19 的 `fsnotify_ops.handle_event`，保留延迟清理监控器的行为。
- 修复 `susfs_get_enabled_features()` 分配失败后的空指针访问。
- sdcard 监控初始化失败时关闭 early-boot static key，避免后续每次 exec 都走早期启动路径。
- 沿用本内核 `vfs_create_mount()` 的分配点，保留完整的 superblock/root 初始化。
- 挂载控制接入 v2.2 static key、高位 mount ID 和内核原生 ID 分配器。
- exec/access/stat 组合钩子适配固定 SukiSU `builtin` 的 bool/static-key 类型。
- Linux 4.19 SELinux 策略更新后调用 `susfs_set_batch_sid()`，使 zygote 子进程获得 Manager fd 和预期的 seccomp 处理。

这些适配保存在静态组合补丁中，由 CI 检查。

## v2.3 的变化

v2.3 使用官方头文件与核心，继续适配 4.19 的 fsnotify 回调和 sdcard 监控失败清理。分配失败修复已进入上游，因此移除了旧的本地补丁。

Kstat 接入旧 VFS 时，需要区分 FUSE 与普通 inode 标记，在文件系统 getattr 回调之后伪装属性；返回缓存的文件系统数据前，仍执行 statfs 安全检查。补丁还提供核心所需的 statfs/flags 包装，在 inotify 和 proc fdinfo 中处理 inode、设备与挂载身份，并允许 zygote、zygote_next 中已卸载挂载的应用解析原挂载。

Linux 4.19 没有现代 statx mount ID。官方核心按内核版本保护对应字段，移植将私有 Kstat 标记直接传给核心，保持 syscall 结果掩码和公开结构布局不变。

## 早期移植的构建检查

以下是 v2.2 移植时采用的审计顺序，保留用于复查历史产物。当前工作流和固定输入以仓库代码为准。

1. 核对原始工作流 Git blob 按 LF 归一化后的 SHA-256：`cd654904e8bf96032c1990ada83125894ece23daf41cdba7da514fd17d6afe31`，先构建未改动的无 SUSFS 基线。
2. 用 `git apply --check` 检查组合补丁，拒绝 fuzz、三方合并、构建时改写源码及白名单之外的文件。
3. 关闭 KPM、kprobes 和全部 SUSFS 子选项，再启用所选配置。
4. 先构建 `smoke`，通过后构建 `minimal-mount`。`extended-stat` 再核对三个已真机批准的补丁 blob 与 `73c1484584a40dd41a9ccc2d0593d47de5b66dc6` 完全相同，只新增 `CONFIG_KSU_SUSFS_SUS_KSTAT`。`extended-full` 使用同一补丁检查，启用官方 v2.2 的九项功能。
5. 检查 Manual Hook、SUSFS 符号、现代与 4.19 SID-cache 调用点，对比最终配置、`System.map` 和 Image 大小；编译警告或异常增长会阻断构建。
6. 单独构建固定版本的 `ksu_susfs` 工具。产物通过短期 Actions artifact 发布，附 SHA-256 和 provenance。

Try Umount、自动添加挂载和 OverlayFS 等已废弃选项不在九项功能之内。

## 早期真机测试流程

当时按 `smoke`、`minimal-mount`、`extended-stat`、`extended-full` 逐级测试，每级单独记录结果：

1. 读取活动槽位，备份并计算 `boot_a`、`boot_b` 的哈希，保留可直接恢复的原活动分区镜像。检查电量、USB、ADB、Fastboot，并用 `fastboot getvar unlocked` 确认 Bootloader 解锁。
2. 首次启动关闭外部 `susfs4ksu` 模块，使用 SukiSU Safe Mode 隔离其他模块。只替换当前 boot 副本中的 `Image`，保留 ramdisk、DTB、DTBO、`vendor_boot`、`init_boot` 和 SELinux 状态。
3. 先 `fastboot boot` 临时启动；无法临时启动则停止。`smoke` 要求五分钟内正常开机，检查 ADB/root、SELinux Enforcing、存储解密、SUSFS 版本及功能、网络、相机、指纹、音频、充电、文件读写和内核日志。
4. 通过后才将同一镜像写入原活动槽位，保留另一槽位。计划要求三次冷启动及至少 24 小时观察，再推进到下一档；完成情况见下方实际记录。
5. `extended-stat` 首次启动时清空持久化 Kstat 规则，确认功能列表只新增 `SUS_KSTAT`，再用一个临时文件测试规则。`extended-full` 首次启动关闭用户态模块，清空全部规则和伪装值，确认功能列表后再逐项配置。

出现 panic、oops、BUG、UAF、lockup、SELinux 或功能回归时，恢复原活动槽位 boot，保存 dmesg/pstore 后停止该轮测试。

## v2.2 extended-full 实际测试记录

工作流提交 `c60b11c91935` 的产物通过 CI 审计后，将其内核替换进保存的原活动槽位 boot 镜像，先用 `fastboot boot` 启动。第一次隔离测试中，Android 完成启动，SukiSU root、SELinux Enforcing 和加密存储正常。固定的官方 `ksu_susfs` v2.2 工具报告 `v2.2.0`、`NON-GKI` 及以下九项功能：

```text
CONFIG_KSU_SUSFS_SUS_PATH
CONFIG_KSU_SUSFS_SUS_MOUNT
CONFIG_KSU_SUSFS_SUS_KSTAT
CONFIG_KSU_SUSFS_SPOOF_UNAME
CONFIG_KSU_SUSFS_ENABLE_LOG
CONFIG_KSU_SUSFS_HIDE_KSU_SUSFS_SYMBOLS
CONFIG_KSU_SUSFS_SPOOF_CMDLINE_OR_BOOTCONFIG
CONFIG_KSU_SUSFS_OPEN_REDIRECT
CONFIG_KSU_SUSFS_SUS_MAP
```

第一次启动时，外部 `susfs4ksu v2.2.0-R28` 模块保持关闭。pstore 为空，日志扫描未发现 panic、oops、BUG、UAF 或 lockup；测试者反馈网络、相机、指纹、音频、文件读写正常。基线已有的显示驱动 GPIO 诊断未计为 SUSFS 回归。

随后将同一重打包镜像写入原活动槽位 `boot_b`：

| 镜像 | SHA-256 |
| --- | --- |
| 测试并写入的 boot | `a01d5add6f898fa756585c35c51c49b9687eb10501f81c1d7170064f379fcac3` |
| 原始 boot_b 备份 | `37ccb46cc368027e2fef746577859b414d9963041956c093cb69fc72df107bae` |

未切换槽位。模块仍关闭时，安装后的镜像完成一次正常启动，root、SELinux、存储和文件读写正常，pstore 与致命错误扫描为空。

启用用户态模块前，确认 `sus_path.txt`、`sus_path_loop.txt`、`sus_maps.txt`、`sus_mount.txt`、`try_umount.txt`、`sus_open_redirect.txt` 的非注释条目为空，`sus_kstat_statically.json` 为 `[]`，全部可选伪装值为 0。启用 `susfs4ksu v2.2.0-R28` 后再次正常启动，模块启动标记、boot-stage 日志和 sdcard 监控均出现，九项功能启用，已废弃选项仍标记为 deprecated。root、SELinux Enforcing、存储和文件读写正常，pstore 与致命错误扫描仍为空。

这轮记录未覆盖自定义规则和伪装值、反复物理冷启动或长时间观察，也未直接刷入 Actions ZIP。它记录的是上述 v2.2 产物的测试结果。
