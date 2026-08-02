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
4. 确认 dmesg/pstore 无异常后再启用开关并重启一次。
5. 分别验证开启和关闭状态；出现任何异常立即恢复当前 `main` 的 boot 备份。

本仓库不会自动启动、刷写、切换槽位或覆盖两个 boot 分区。真机测试完成前，
不得把该功能标记为稳定或合并到 `main`。
