# OnePlus 8T — LineageOS 24.0 实验性 SukiSU 内核

此分支为 OnePlus 8T（`kebab`，目标型号 KB2000）提供 LineageOS 24.0 /
Android 17 的实验性支持，尚未完成 Android 17 真机验证。

正式主线在迁移批准前仍支持 23.2。23.2 上已有的启动与硬件检查记录，不能作为
24.0 的验证结果。完整迁移计划见 [实验说明](docs/LINEAGE-24-EXPERIMENT.md)。

## 固定输入

| 项目 | 当前目标 |
| --- | --- |
| 系统 | LineageOS 24.0 / Android 17 / API 37 |
| 内核 | 官方 `lineage-24.0`，Linux 4.19；完整 SHA 见 `pins/kernel-lineage-24.0` |
| 配置 | `vendor/kona-perf_defconfig` + `vendor/oplus.config` |
| Root | SukiSU Ultra `builtin`，41001 |
| SUSFS | v2.3，NON-GKI，Inline Hook |
| 编译器 | Android Clang r563880，LLVM integrated assembler |
| KPM / kprobes | 关闭 |

SukiSU、SUSFS、Clang、NDK 与 AnyKernel3 沿用迁移起点的固定版本。
此次不因 Android 版本号变化重写 Root Hook 或更换工具链。

## 构建与核验

实验 PR 自动构建四种配置：纯 SukiSU、SELinux hide、SUSFS extended-stat、
以及 extended-full + SELinux hide。继续检查补丁落点、配置、符号、警告和 Image 大小。

也可在 **Build kebab SukiSU Ultra** 中明确选择 `experiment/lineage-24.0`
手动构建。该分支产物使用 `CANDIDATE_`，文件名含 `LOS24.0`；选择
`latest-lineage-24.0` 时使用 `UNAPPROVED_LATEST_`。后者不会更新固定书签。
实验分支不能生成主线 approved 通道产物。

SUSFS 与 SELinux hide 仍可分别关闭。SUSFS 支持 smoke、minimal-mount、
extended-stat、extended-full 档位；默认 extended-full。编译选项开启不代表
自定义隐藏规则已配置。首次测试保持自定义规则为空。

构建指纹、provenance 和批准记录均区分目标平台。即使上游 23.2 / 24.0 内核
提交相同，平台迁移也会检查目标 ref，并要求新的 Android 17 真机结果。

## 真机验证与采用条件

只使用与所安装 24.0 构建匹配的原始 boot 制作测试镜像，仅替换其中的 Image，
保留 ramdisk、DTB 和 DTBO。先临时启动，再检查 Root、SELinux Enforcing、
存储解密、网络、相机、指纹、音频、SUSFS 与隐藏开关、冷启动及内核日志。
Zygisk / 模块兼容性单独检查。

云端成功不能代替真机结果。受信任 main 的验证器先通过独立兼容 PR 支持 24.0，
之后才可核验这个实验候选的精确提交、产物哈希与测试声明。不会自动刷机或切槽。

24.0 通过验证后，先将当时最后的 23.2 main 保存至 `archive/lineage-23.2-final`，
核对远端存档 SHA，再将批准的 24.0 PR 合入 main。当前不提前冻结存档，避免漏掉
实验期间的 23.2 更新。旧 `legacy` / `SUSFS` 分支继续保留其原有历史含义。

## 实现与历史记录

- [24.0 实验及迁移计划](docs/LINEAGE-24-EXPERIMENT.md)
- [SUSFS 移植与历史检查](docs/SUSFS-EXPERIMENT.md)
- [SELinux hide 实现与历史检查](docs/SELINUX-HIDE-EXPERIMENT.md)
- [迁移起点的上游更新记录](docs/UPSTREAMS-20261017.md)

这些历史文档中的 23.2 真机结果保留原义，不代表本实验已获批准。
