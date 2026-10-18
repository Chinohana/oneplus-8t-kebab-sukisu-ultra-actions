# 2026-10-17 上游更新与 Manager 兼容修复

这次更新将 SukiSU `builtin` 与 Manager 对齐到 41001，并更新 SUSFS v2.3。它延续 [PR #25](https://github.com/Chinohana/oneplus-8t-kebab-sukisu-ultra-actions/pull/25) 的依赖升级，之后成为 [LineageOS 24.0 迁移](LINEAGE-24-EXPERIMENT.md)的输入基线。

## 选定版本

| 输入 | 提交或版本 | 当时的变更 |
| --- | --- | --- |
| LineageOS `lineage-23.2` | `98a7970af93b7e01ee77156e7fa0eb7e059a57f0` | 核对时仍为上游分支最新提交 |
| SukiSU `builtin` | `0af2cf9cef7dc2239fa7ebb3f7898830a1087e26` | 新增七个提交，涉及动态 Manager 授权、强制功能、仅 ADB shell root |
| SukiSU Manager | `2aed04fcfdff9ad53041ffd84a291573993fa538`，`v4.2.1_41001` | 模块及 Manager 工作流更新 |
| SUSFS v2.3 | `5369359dbd10f6dd8cbdd59d1df7b788b29b168c` | 修复 SELinux status-open 顺序，移除未使用的 GKI 辅助代码 |
| AnyKernel3 | `020dfeccf9d7e962a48400fc94d3e451df92eead` | 核对时仍为上游 HEAD |
| Clang / NDK | `r563880` / `27.2.12479018` | 沿用已选版本 |

内核继续使用支持 Manual Hook 的 SukiSU `builtin` 分支。旧构建器和 SM8250 补丁落点提交保留为审计参考。

## Manager 与 4.19 兼容

[Manager 构建 38760810020](https://github.com/SukiSU-Ultra/SukiSU-Ultra/actions/runs/38760810020) 的普通产物为 `SukiSU_v4.2.1_41001-release.apk`，SHA-256：

```text
cd4945d3f4491ea2869ed374887202c85154a86205dd04d81991bf4dc4340d6f
```

该版本更新了模块仓库、动态 Manager、一次性脚本、热安装和界面，因此驱动版本随之调整到 41001。此次对比下载并检查了 APK，没有在手机上安装。

两份 Linux 4.19 兼容补丁重基到新 `builtin` 源码，保留上游动态 Manager 初始化与加载调用、仅 ADB shell root 注册，以及 UAPI version 5、su-session 和 SELinux 适配。强制功能重试保留在现代 SELinux 回调的版本保护之外；4.19 未定义 SELinux hide 枚举时，对功能名称表中的对应项加条件保护。

## 第一次构建为何失败

此前候选 `0d23ba58` 的四种配置已在构建 `38285889576` 中通过。更新后的首次构建 `39021969061`（PR 提交 `151a0f23`）又遇到三个 `builtin` 遗漏：APK 包名缓冲区超出作用域、observer 使用了不存在于 builtin 布尔接口的扫描常量，以及缺少动态 Manager ioctl 声明。

兼容补丁改为在两种授权路径前提取候选 APK 包名。内置候选仅处理内置包名；动态候选先匹配实际包名，再检查注册 UID 和证书。observer task work 使用 `track_throne(false)` 完整同步扫描。Manager ioctl 106 沿用参考 UAPI 的 `_IOWR` 编码和结构。

## 授权测试

`scripts/test-manager-crown.py` 使用宿主环境桩编译实际打补丁后的授权函数，覆盖十种情况：有效动态候选、有效内置候选、错误签名、错误注册 UID、跨包复用证书、未知包、关闭动态授权、内置候选优先级与失败处理、已验证签名回退、包解析失败。

两种准备好的内核源码树都会在云端编译前运行这些检查。APK 扫描和完整运行时行为仍由真机测试覆盖。

## SUSFS 的 status-open 顺序

这次官方改动位于集成补丁，v2.3 核心和两份头文件未变。修复让 status-open 优先选择已初始化的假状态页，然后才处理延迟初始化。

4.19 移植的 `ksu_sel_open_handle_status` 已按这个顺序工作：先选已有假页；没有假页时调用原 status-open，由它先设置真实页，再尝试延迟初始化。假状态页保留到内核生命周期结束，因此本次不需要改动这条 4.19 路径。上游删除的 GKI 专用辅助代码也不影响它。

两份重基后的 SukiSU 补丁通过了严格应用检查，上游动态 Manager、强制功能调用点保留，v2.3 kernel/exec/SELinux 补丁顺序未变。这些是更新时的补丁检查结果；后续四种云端构建和 Android 17 真机批准记录见 [24.0 迁移记录](LINEAGE-24-EXPERIMENT.md)。
