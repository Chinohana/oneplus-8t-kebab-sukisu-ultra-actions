# 在自己的 GitHub 仓库构建特定配置

维护者默认只提供 `extended-full + SELinux hide` 完整功能版。需要精简 SUSFS、关闭 SUSFS 或关闭 SELinux hide 时，可克隆项目后推送到自己的 GitHub 仓库，或直接 Fork，再使用 GitHub Actions。

## 操作步骤

1. 在 GitHub Fork 本项目。也可以先 `git clone`，再将源码推送到自己有写权限的 GitHub 仓库；仅本地克隆不会运行 Actions。
2. 在自己的仓库打开 **Actions**，按 GitHub 提示启用工作流。
3. 选择 **Build kebab SukiSU Ultra**，点击 **Run workflow**，选择包含当前构建工具的分支。
4. 按需设置 SUSFS、SUSFS profile 和 SELinux hide。默认值仍为 SUSFS 开启、`extended-full`、SELinux hide 开启。
5. 完成后，在该次运行的 **Artifacts** 下载产物。构建失败时查看日志和诊断附件。

| 参数 | 选择 |
| --- | --- |
| `enable_susfs` | 是否编译 SUSFS |
| `susfs_profile` | `smoke`、`minimal-mount`、`extended-stat` 或 `extended-full`；关闭 SUSFS 时忽略 |
| `enable_selinux_hide` | 是否包含本项目的 4.19 SELinux hide 支持 |

一次运行只编译选定配置的一个 Image，打包为 AnyKernel3 ZIP。工作流手动触发，不从 PR 或 push 自动构建，不创建 Release。主仓库不运行这个自定义编译任务，仍由维护者在本地准备完整功能版。

## 下载与验证

Artifact 是 GitHub 包装的产物归档。解压后，`kernel/` 中的内核 ZIP 才是安装包；`selected.config`、System.map、审计日志和 provenance 用于核对来源。开启 SUSFS 时，`tool/` 还包含重新编译的用户态工具。

工作流使用仓库 pins 中的精确提交和工具链。需要指定历史版本时，选择包含相应 pins 与兼容补丁的源码提交；只更改版本号不能代替移植。云端构建通过不代表已经在设备上测试，安装前核对设备、ROM、哈希并准备 boot 备份。

“全部功能”指本项目当前适配的 SukiSU、SUSFS 子功能和 SELinux hide。KPM 与 kprobes 仍关闭，不提供尚未完成 4.19 适配的开关。
