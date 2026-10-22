# LineageOS 24.0 迁移记录

本文是历史移植和验证记录。当前编译、验收和发布全部在本地执行，操作入口见[本地构建说明](LOCAL-BUILD.md)；下文保留的云端步骤只用于追溯。

2026-10-18，OnePlus 8T（`kebab` / KB2000）的 LineageOS 24.0 内核完成真机批准并合入 `main`。测试系统为 `24.0-20261016-NIGHTLY-kebab`，Android 17 / API 37；机主在持续使用后确认运行稳定。

## 迁移改了什么

迁移从 23.2 主线提交 `7cad005b0ff85497d2c80171725022ce95062db8` 开始。2026-10-17 核对上游时，`lineage-23.2` 和 `lineage-24.0` 都指向 `98a7970af93b7e01ee77156e7fa0eb7e059a57f0`，因此新的 24.0 内核书签沿用了这个提交。

SukiSU `builtin` 41001、SUSFS v2.3、Clang r563880、NDK 和 AnyKernel3 沿用迁移起点的固定版本。内核源码相同，本次没有为 Android 17 重写 Root Hook。

改动集中在目标平台：切换上游分支和内核书签，让构建指纹、包名、provenance 和批准记录区分 ROM 版本。平台切换时，即使内核 SHA 相同，也会核验上游 ref 并要求新的真机结果。

云端构建了纯 SukiSU、SELinux hide、SUSFS `extended-stat`、`extended-full + SELinux hide` 四种组合。实验分支 `experiment/lineage-24.0` 的手动构建使用 `CANDIDATE_` 通道。

## 构建与批准

先通过独立的 `support/lineage-24-approval` 分支，让受信任的主线验证器识别 24.0 产物，同时保留对旧 23.2 产物的支持；再核验 24.0 候选。验证器使用主线代码，不执行候选仓库中的代码。

| 记录 | 标识 |
| --- | --- |
| 真机测试候选 | `7243b36efb97f858ed9332b689298ae543ff58a7` |
| 四种配置构建 | [39033909465](https://github.com/Chinohana/oneplus-8t-kebab-sukisu-ultra-actions/actions/runs/39033909465)、[39103352341](https://github.com/Chinohana/oneplus-8t-kebab-sukisu-ultra-actions/actions/runs/39103352341)，均通过 |
| 真机批准 | [39103292520](https://github.com/Chinohana/oneplus-8t-kebab-sukisu-ultra-actions/actions/runs/39103292520)，机主确认后核验通过 |
| 手机活动 boot 分区的 Image SHA-256 | `f49876ef3cd48e8b0462e663c1871857707da8e9fad0c8dcca1ce3be0a86e913` |
| 批准的 ZIP SHA-256 | `9377d0b3fd26566f6b137feceb3b226e67d5be558806bb4722dc3498de529443` |

手机中的内核 Image 与批准候选的哈希一致。

## 真机结果与模块问题

已检查 root、SELinux Enforcing、SUSFS 功能与隐藏开关、加密存储、连接状态及前后相机预览。隔离模块和恢复模块后各完成了一次普通重启。这轮检查没有覆盖全部硬件功能和第三方模块组合。

测试期间，TA Enhanced v5.53.1 停止了 LineageOS 必需的充电 HAL，导致软重启卡在启动阶段；SELinux hide 开启、关闭时都会出现。重新启动 HAL 后，系统继续启动。随后仅移除模块中的停服务代码，保持内核不变、SELinux hide 开启，两次连续软重启通过。

问题已报至 [TA Enhanced #46](https://github.com/Enginex0/tricky-addon-enhanced/issues/46)。模块更新可能覆盖手机上的临时修正。

早期日志中还有两个未定位的问题：`mem_cgroup_update_lru_size` 警告，以及启用模块时的 Java 异常 `ClassNotFoundException: android.security.keystore.KeyStoreException`。机主接受本次迁移时保留了这两项记录；后续稳定使用没有证明它们已经修复。原始手机日志保存在本地。

## 主线切换与 23.2 归档

合并前，先将最终 23.2 主线保存到 `archive/lineage-23.2-final`，并核对远端指向 `c779ee8c6287a37b21e0eb8ee43e80e7a673043b`。随后合并 [PR #27](https://github.com/Chinohana/oneplus-8t-kebab-sukisu-ultra-actions/pull/27)，合并提交为 `db51e6e710fd9aa1e7bcf529ba9fca05f4027e67`。

## 后续候选怎样测试

使用与手机已安装的 24.0 构建匹配的原始 boot 镜像，备份恢复文件，只替换其中的内核，保留 ramdisk、DTB 和 DTBO。先用 `fastboot boot` 临时启动，保持原活动槽位。

检查 ADB、存储解密、SELinux Enforcing、root 授权与 Manager 通信、网络、相机、指纹、音频、SUSFS、SELinux hide 开关、重复冷启动及 dmesg/pstore。Zygisk 和模块兼容性另行测试。批准记录应对应实际测试的候选提交、产物哈希和 Android 17 环境。
