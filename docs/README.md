# 文档入口

[本地构建说明](LOCAL-BUILD.md) 是当前操作手册，包含环境预检、完整配置编译、真机记录、验收和发布目录生成。

维护者只在本地编译和发布完整功能版。需要特定配置时，克隆后推送或 Fork 到自己的仓库，再按[自定义构建说明](CUSTOM-BUILD.md)运行 GitHub Actions。主仓库的 PR 继续只运行轻量检查；旧云端审批步骤不再适用。

[2026-10-25 上游同步](UPSTREAMS-20261025.md) 记录 SUSFS priority UID filter 移植和 Manager 版本选择。[2026-10-24 上游同步](UPSTREAMS-20261024.md) 保留此前依赖与验收记录。[本地空间实测](LOCAL-STORAGE-20261024.md) 记录取消默认容量门槛后的完整构建、文件数和占用。

[2026-10-27 构建策略](BUILD-POLICY-20261027.md) 记录单一完整配置与自定义 Actions 的分工，以及重新核实的上游 Manager 版本。

[2026-10-27 本地编译性能](BUILD-PERFORMANCE-20261027.md) 记录与 AirDrop 构建方式的对照、缓存修复和冷、热两轮实测。

## 历史移植记录

以下文档保留当时的提交、问题和测试结果。需要核对旧产物或理解补丁来源时再查阅，不照搬其中的工作流入口。

| 文档 | 内容 |
| --- | --- |
| [SUSFS 移植记录](SUSFS-EXPERIMENT.md) | NON-GKI、手动 hook 和功能配置 |
| [SELinux hide 移植记录](SELINUX-HIDE-EXPERIMENT.md) | Linux 4.19 适配和早期验证 |
| [LineageOS 24.0 迁移](LINEAGE-24-EXPERIMENT.md) | 平台迁移、真机测试及当时的批准过程 |
| [2026-10-17 上游记录](UPSTREAMS-20261017.md) | 当日依赖和兼容性检查 |
| [2026-10-19 上游记录](UPSTREAMS-20261019.md) | SukiSU 41028、SUSFS 同步和适配 |
