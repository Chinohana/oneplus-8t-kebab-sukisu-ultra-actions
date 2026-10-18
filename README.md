# OnePlus 8T — LineageOS 24.0 SukiSU 内核

主线为 OnePlus 8T（`kebab`，已测型号 KB2000）提供 LineageOS 24.0 /
Android 17 支持。2026-10-18，机主确认持续使用稳定，完成真机批准并合入主线。

最后的 23.2 主线保存在 [archive/lineage-23.2-final](https://github.com/Chinohana/oneplus-8t-kebab-sukisu-ultra-actions/tree/archive/lineage-23.2-final)，
对应提交 `c779ee8c6287a37b21e0eb8ee43e80e7a673043b`。
迁移过程与 24.0 验证记录见 [迁移说明](docs/LINEAGE-24-EXPERIMENT.md)。

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

候选 PR 自动构建四种配置：纯 SukiSU、SELinux hide、SUSFS extended-stat、
以及 extended-full + SELinux hide。继续检查补丁落点、配置、符号、警告和 Image 大小。

也可在 **Build kebab SukiSU Ultra** 中选择 `main` 手动构建固定版本。
候选分支产物使用 `CANDIDATE_`，文件名含 `LOS24.0`；选择
`latest-lineage-24.0` 时使用 `UNAPPROVED_LATEST_`。后者不会更新固定书签。
实验分支不能生成主线 approved 通道产物。

SUSFS 与 SELinux hide 仍可分别关闭。SUSFS 支持 smoke、minimal-mount、
extended-stat、extended-full 档位；默认 extended-full。编译选项开启不代表
自定义隐藏规则已配置。首次测试保持自定义规则为空。

构建指纹、provenance 和批准记录均区分目标平台。即使上游 23.2 / 24.0 内核
提交相同，平台迁移也会检查目标 ref，并要求新的 Android 17 真机结果。

## 真机验证

24.0 候选的四种云端配置均构建通过，手机活动启动分区内核与已批准候选 Image
哈希一致。已核对 Root、SELinux Enforcing、SUSFS 功能与隐藏开关、存储解密、
连接状态和前后相机预览，并完成模块隔离、恢复后的普通重启。

软重启卡启动来自 TA Enhanced 停止 LineageOS 充电 HAL；移除该模块的停服务
代码后，两次软重启通过，SELinux hide 保持开启。问题已报至
[TA Enhanced #46](https://github.com/Enginex0/tricky-addon-enhanced/issues/46)，
模块更新可能覆盖手机上的临时修正。

早期日志中的一次 memcg 警告和启用模块时的 Java 异常仍未定位；后续稳定使用
不代表这些问题已经修复。本次结果也不覆盖所有硬件功能与第三方模块组合。

后续候选仍需按以下流程验证：

只使用与所安装 24.0 构建匹配的原始 boot 制作测试镜像，仅替换其中的 Image，
保留 ramdisk、DTB 和 DTBO。先临时启动，再检查 Root、SELinux Enforcing、
存储解密、网络、相机、指纹、音频、SUSFS 与隐藏开关、冷启动及内核日志。
Zygisk / 模块兼容性单独检查。

云端成功不能代替真机结果。受信任 main 的验证器先通过独立兼容 PR 支持 24.0，
之后才可核验这个实验候选的精确提交、产物哈希与测试声明。不会自动刷机或切槽。

24.0 迁移已按先归档 23.2、核对远端 SHA、再合并已批准候选的顺序完成。
旧 `legacy` / `SUSFS` 分支继续保留其原有历史含义。

## 实现与历史记录

- [24.0 实验及迁移计划](docs/LINEAGE-24-EXPERIMENT.md)
- [SUSFS 移植与历史检查](docs/SUSFS-EXPERIMENT.md)
- [SELinux hide 实现与历史检查](docs/SELINUX-HIDE-EXPERIMENT.md)
- [迁移起点的上游更新记录](docs/UPSTREAMS-20261017.md)

历史文档中的 23.2 真机结果保留原义；24.0 使用独立的候选核验与真机批准记录。
