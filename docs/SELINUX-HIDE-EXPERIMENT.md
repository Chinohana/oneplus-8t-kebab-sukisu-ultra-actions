# Linux 4.19 的 SELinux hide 移植

本项目通过 `CONFIG_KSU_SELINUX_HIDE_4_19` 接入 SukiSU 的“隐藏 SELinux 修改”。该功能已合入 `main`，默认编译，运行时在管理器中手动开启；构建时可用 **Enable SELinux hide** 关闭。

它让应用读取 KSU 规则注入前的 SELinux 策略快照，系统进程和 root 仍使用实时策略。实际 Enforcing 状态和 SUSFS 的 AVC 日志伪装不受这个开关影响。

下文记录 OnePlus 8T / LineageOS 23.2 上的移植事故和复验。LineageOS 24.0 的验证另见[迁移记录](LINEAGE-24-EXPERIMENT.md)。

## 启动卡死：错误地钩住了 setprocattr

2026-08-05，开启隐藏功能后，两次冷启动都卡在“手机正在启动”。此前将功能标记为“验证成功”的结论有误。

崩溃发生在 Zygote 为应用设置 SELinux 上下文时。`org.codeaurora.ims`（UID 10149）等应用反复 abort，日志包含：

```text
frameworks/.../Zygote.cpp:2152: selinux_android_setcontext(...) failed
```

4.19 移植额外钩住了 `selinux_setprocattr`，将应用 UID（≥10000）写入 `/proc/self/attr/current` 的操作重定向到假策略。假策略及假 sidtab 无法完成 Zygote 所需的上下文转换，应用启动失败，system_server 看门狗持续触发。

官方 SukiSU 的隐藏功能只钩 selinuxfs 的 policy/status/context/access，不钩 `setprocattr`。修复删除了 `security/selinux/hooks.c` 中的全部 `setprocattr` 重定向，让 Zygote 恢复使用真实策略；其余 selinuxfs 隐藏路径保留真实策略的权限检查。

此前补齐 `fake_state` 字段、加入“queued for the next boot”状态机没有解决卡死。修复保留了 `fake_state = selinux_state` 整体复制和快照失败时保持关闭的状态处理。设备在关闭功能后先恢复正常，再进行修复构建和复验。

## 2026-08-06 复验

提交 `3ae092c` 通过完整 CI 审计后，在开发机 `boot_b` 上完成两轮冷启动：

- 关闭和开启功能均可进入系统，Lawnchair 正常显示，可列出 316 个应用包。
- `org.codeaurora.ims` 等 Zygote 应用正常启动，crash 日志中的 `selinux_android_setcontext` 失败次数为 0。
- dmesg 确认 `ksu_selinux_hide_running: 1`；仅有一次启动期 watchdog 心跳，没有持续触发，pstore 为空。
- 应用读取 policy/status 得到干净策略和独立状态页，哈希与 root、系统进程不同。
- SELinux 全程 Enforcing，root、SUSFS、vold、netd、surfaceflinger 正常。

这次复验确认移除 `setprocattr` 钩子后，应用启动和隐藏语义均恢复正常。当时产物仍标记为 `EXPERIMENTAL`，功能在之后才并入主线。

## 实现

KSU 写入规则前，先序列化并重新解析原始 policydb，建立独立的只读 `selinux_ss`、sidtab 和 class mapping。快照失败时保持功能关闭。

应用 UID（≥10000）的 status、policy、context/access 查询使用快照；系统进程和关闭状态使用真实策略。`setprocattr` 始终使用真实策略。

钩子使用源码中的条件分支，不依赖 kprobe、KPM、运行时 text patch 或符号扫描。关闭开关只停止使用快照；可能已被 mmap 的 fake status 页会保留到内核生命周期结束。

## 开关测试

先核对测试产物的 SHA-256，保持管理器开关关闭，用 `fastboot boot` 临时启动。确认系统、ADB、root、存储解密、SELinux Enforcing、SUSFS、主要硬件及 dmesg/pstore 正常后，再测试开关。

若系统已经完成启动，开启请求会标记为“下次启动启用”，当前启动周期仍保持关闭。重启后，内核在 KSU 规则注入前建立并启用干净快照。分别检查开启和关闭状态；出现启动或功能异常时，恢复测试前备份的原活动槽位 boot 镜像。
