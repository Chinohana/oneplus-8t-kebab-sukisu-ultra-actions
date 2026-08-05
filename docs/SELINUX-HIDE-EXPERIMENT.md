# Linux 4.19 隐藏 SELinux 修改实验

> [!CAUTION]
> 这是 OnePlus 8T（kebab / KB2000）、LineageOS 23.2 和固定 Linux 4.19
> 内核的实验性回移植。它尚未完成真机启动验证，不可用于其他设备或 ROM。

## 当前状态

手机当前使用的 `main` 内核仍保持 SELinux Enforcing，SukiSU 管理器中的
“隐藏 SELinux 修改”显示“内核不支持此特性”。这是因为固定的 SukiSU
`b1d534bc` 只在 Linux 5.10 及以上注册该功能。

本实验通过 `CONFIG_KSU_SELINUX_HIDE_4_19` 单独启用 4.19 回移植。该配置不会
改变 SELinux 的实际 enforcing 状态，也不会修改 SUSFS 的 AVC 日志伪装。

> [!IMPORTANT] 2026-08-05 真机事故与已修复根因
>
> 在开发机上一次开启功能并冷启动后，出现“第二启动屏幕比平时更久，随后停在
> 『手机正在启动』”的卡死，无法进入系统。已经确认两个直接相关因素：
>
> 1. 旧版 4.19 适配在 `ksu_selinux_hide_enable()` 中只初始化了
>    `fake_state.initialized/ss/avc`，其余字段为零。在 `CONFIG_SECURITY_SELINUX_DEVELOP`
>    下零值 `enforcing=false` 会让隐藏查询路径对应用呈现出 permissive 语义，
>    与“不改变真实策略限制”的设计目标相悖，并显著放大策略转换/状态页路径的
>    异常面，是本次卡死最可疑的代码缺陷。
> 2. 管理器点击“开启”是在 boot-complete 之后，此时内核已释放干净策略备份；
>    `EAGAIN` 会导致开关状态与内核实际运行状态不一致（已通过“queued for the
>    next boot”状态机修复）。
>
> 修复内容（实验分支 `experiment/selinux-hide-sm8250-4.19`）：
>
> - 4.19 启用时先 `fake_state = selinux_state` 整体复制实时控制平面，再仅替换
>   `ss`，并重新确认 `initialized`，保证 enforcing/checkreqprot/policycaps 等
>   字段与真实状态一致；
> - 保持 fail-closed：备份缺失时 `running=false`，真实 SELinux 继续工作；
> - CI 新增静态断言，要求 4.19 路径必须包含上述整体复制，防止回退。
>
> 事故后已通过 Fastboot 将开发机恢复到已知良好 `main` 内核（`boot_b`
> SHA-256 `a01d5add…fcac3`），当前设备正常、SELinux Enforcing、root 正常，
> pstore 为空。重新开始真机验证前，必须先重新构建并通过完整 CI 审计。

## 实现边界

- 在 KSU 规则写入前序列化并重新解析原始 SELinux policydb，建立独立的只读
  `selinux_ss`、sidtab 和 class mapping；快照失败时保持功能关闭。
- 对应用 UID（10000 及以上）的 SELinux status、policy、context/access 查询和
  `attr/current` 校验使用快照；系统进程及关闭状态使用真实策略。
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
