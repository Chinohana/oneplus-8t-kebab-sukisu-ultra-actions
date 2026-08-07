# Linux 4.19 隐藏 SELinux 修改实验

> [!CAUTION]
> 这是 OnePlus 8T（kebab / KB2000）、LineageOS 23.2 和固定 Linux 4.19
> 内核的实验性回移植。它尚未完成真机启动验证，不可用于其他设备或 ROM。

## 当前状态

本实验通过 `CONFIG_KSU_SELINUX_HIDE_4_19` 单独启用 SukiSU“隐藏 SELinux
修改”的 Linux 4.19 回移植。该配置不会改变 SELinux 的实际 enforcing 状态，
也不会修改 SUSFS 的 AVC 日志伪装。该功能已并入 `main` 并默认包含在
**Build kebab SukiSU Ultra** 工作流产物中；开关默认不自动启用，需要时在
管理器中手动开启。不需要该功能时，构建时关闭 **Enable SELinux hide** 选项。

### 2026-08-05 真机状态（重要更正）

此前的“验证成功”结论是错误的。实际开启功能后系统仍会卡在“手机正在启动”，
根因是 4.19 移植额外钩住了 `selinux_setprocattr`（`/proc/self/attr/current`）：
Zygote 为应用（UID ≥ 10000）设置 SELinux 上下文时被重定向到假策略，导致
`selinux_android_setcontext()` 失败、`org.codeaurora.ims` 等应用反复崩溃，
system_server 看门狗持续触发，系统无法完成启动。官方 SukiSU 的隐藏功能
只钩 selinuxfs（policy/status/context/access），从不钩 `setprocattr`。

当前修复（实验分支最新提交）：

- 删除 `security/selinux/hooks.c` 中所有 `setprocattr` 重定向改动，恢复
  Zygote 使用真实策略为应用设置上下文；
- 保留 selinuxfs 的 policy/status/context/access 隐藏路径（这些路径有真实
  策略的权限检查兜底，不会影响应用启动）；
- 保留 `fake_state = selinux_state` 整体复制与 fail-closed 状态机。

设备已通过关闭功能恢复正常（`org.codeaurora.ims` 正常运行）。在重新构建、
CI 审计并确认应用可正常启动之前，不得再次把该功能标记为可用。

### 2026-08-06 真机复验通过（提交 `3ae092c`）

修复 `setprocattr` 钩子后重新构建并通过完整 CI 审计，在开发机 `boot_b`
上完成两轮冷启动复验：

- 功能关闭/开启状态均正常进入系统，桌面（Lawnchair）可见，可列出 316 个
  应用包；
- 功能开启后 `org.codeaurora.ims`（uid 10149）等 Zygote 应用正常启动，
  crash 日志中 `selinux_android_setcontext` 失败次数为 0，不再崩溃循环；
- 内核日志确认 `ksu_selinux_hide_running: 1`；dmesg 仅有一次启动期
  watchdog 心跳（正常），无持续看门狗触发；pstore 为空；
- 隐藏语义仍生效：应用 UID 读取 policy/status 得到无 KSU 规则的干净策略与
  独立状态页（哈希与 root/系统不同），系统进程与 root 使用实时策略；
- SELinux 全程 Enforcing，root、SUSFS、vold/netd/surfaceflinger 正常。

> 结论：`setprocattr` 钩子是“手机正在启动”卡死的真正原因，已移除并复验
> 通过。实验分支产物仍标记为 EXPERIMENTAL，未合并 main。

> [!IMPORTANT] 2026-08-05 真机事故与根因
>
> 开启功能后冷启动两次都卡在“手机正在启动”，system_server 看门狗持续触发。
> 崩溃日志显示 `org.codeaurora.ims`（uid 10149）在 Zygote
> `selinux_android_setcontext()` 处反复 abort：
> `frameworks/.../Zygote.cpp:2152: selinux_android_setcontext(...) failed`。
> 原因确认：4.19 移植错误地钩住了 `selinux_setprocattr`，把应用 UID 写入
> `/proc/self/attr/current` 重定向到假策略，而假策略/假 sidtab 无法完成 Zygote
> 需要的上下文转换，导致每个由 Zygote 启动的应用（UID ≥ 10000）直接崩溃。
>
> 之前的 `fake_state` 字段补齐与“queued for the next boot”状态机是必要的
> 加固，但不是卡死根因；卡死根因已通过删除 `setprocattr` 钩子修复。
> 设备已在关闭功能后恢复（应用可正常启动）。

## 实现边界

- 在 KSU 规则写入前序列化并重新解析原始 SELinux policydb，建立独立的只读
  `selinux_ss`、sidtab 和 class mapping；快照失败时保持功能关闭。
- 对应用 UID（10000 及以上）的 SELinux status、policy、context/access 查询
  使用快照；系统进程及关闭状态使用真实策略。`setprocattr`（应用上下文写入）
  始终使用真实策略，否则 Zygote 无法为应用设置上下文。
- 所有落点均为源码级条件分支，不使用 kprobe、KPM、运行时 text patch 或符号扫描。
- 关闭开关只停止使用快照，不修改真实策略。可能已被 mmap 的 fake status 页不会在
  运行过程中释放。

## 安全测试顺序

1. 下载名称含 `EXPERIMENTAL-SELINUX-HIDE` 的构建产物并核对 SHA-256。
2. 保持管理器中的开关关闭，仅使用 `fastboot boot` 临时启动；不直接刷写。
3. 验证系统启动、ADB、root、解密存储、SELinux Enforcing、SUSFS 和主要硬件。
4. 确认 dmesg/pstore 无异常后再启用开关。若此时系统已经完成启动，内核会把
   请求安全地标记为“下次启动启用”，当前运行周期仍保持关闭；随后重启一次，
   让新启动在 KSU 规则写入前建立并启用干净策略快照。
5. 分别验证开启和关闭状态；出现任何异常立即恢复当前 `main` 的 boot 备份。

本仓库不会自动启动、刷写、切换槽位或覆盖两个 boot 分区。真机测试完成前，
不得把该功能标记为稳定或合并到 `main`。
