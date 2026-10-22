# 本地构建

本地和 GitHub Actions 使用同一组构建阶段。日常试编译在 `OnePlus8T-Build` 的 Ubuntu 24.04 中运行；正式采纳仍需要云端矩阵复核和真机审批。目录迁移或本地编译通过，都不改变候选包的审批状态。

Windows 编译库位于 `E:\Codex Project\OnePlus8T-Build`。源码、工具链和编译缓存放在该发行版的 `/home/chino/oneplus8t-kernel`，占用 E 盘上的 ext4 虚拟磁盘；Windows 下的 `artifacts` 保存导出的交付物。

## 选择构建提交

Windows 项目中的 `repo-local` 用于修改和提交控制代码，WSL 中的 `control` 用于运行已提交的版本。先把修改提交到分支，再在专用 Ubuntu 中取回明确的提交。工作树有未提交文件时，入口会退出。

```bash
cd ~/oneplus8t-kernel/control
git fetch origin migration/local-build
git checkout --detach FETCH_HEAD
python3 scripts/build/local.py --check-only
python3 scripts/build/local.py
```

后续构建可将示例分支替换为已审查的分支或提交。每次运行会创建独立检出，运行中的脚本不受外部入口文件修改影响。源码、补丁和工具链版本来自该提交的 pins。

默认构建固定内核提交、SUSFS `extended-full`、SELinux hide 和 AnyKernel3 ZIP，并启用 ccache，使用 8 个并行任务。Ubuntu 依赖与云端一致：

```bash
sudo apt update
sudo apt install -y bc bison build-essential ccache cpio curl file flex git jq libelf-dev libssl-dev lz4 ninja-build python3 rsync unzip wget zip xz-utils
```

现有 Clang 和 Linux NDK 可直接复用。新环境先执行 `scripts/build/prepare-workspace.sh <builder-ref>`，再把固定版本的 Linux Clang 和 NDK 压缩包放入编译库的 `downloads`，执行 `scripts/build/install-toolchains.sh`。安装脚本保留下载哈希，并核对 NDK 版本；已有工具链目录需要先检查，脚本不会覆盖。

## 参数与预检

| 参数 | 默认值或用途 |
| --- | --- |
| `--enable-susfs`、`--enable-selinux-hide` | `true`，接受 `true` / `false` |
| `--profile` | `extended-full`；也支持 `smoke`、`minimal-mount`、`extended-stat` |
| `--use-anykernel`、`--use-ccache` | `true`，接受 `true` / `false` |
| `--kernel-source` | `approved-pin`；`latest-lineage-24.0` 核验继承关系后构建未批准候选 |
| `--jobs` | `8` |
| `--workspace` | `~/oneplus8t-kernel`，必须位于 ext4 |
| `--storage`、`--export-dir` | 编译库根目录、产物导出目录 |
| `--clang`、`--ndk` | 指定已安装的 Linux 工具链 |
| `--cache-dir` | 指定持久编译缓存目录 |
| `--kernel-seed`、`--sm8250-seed` | 可选的本地 Git 对象种子；命中固定提交时使用 |
| `--check-only` | 只检查环境，不创建运行目录或启动编译 |
| `--minimum-free-gib` | 默认 `50`，可提高，不能低于 50 GiB |

预检同时检查 Linux 和 Windows 存储可用空间。WSL 中显示的虚拟磁盘容量不能代替宿主 E 盘剩余空间。并行度先保持 `8`，再根据实际内存和耗时调整。

## 日志、交付和重试

运行目录为 `~/oneplus8t-kernel/runs/local-full-时间戳`。完整日志在 `audit/local-pipeline.log`，`audit/local-result.json` 记录阶段退出码、耗时，以及每 5 秒采样的 WSL 内存使用峰值、文件系统使用峰值和宿主剩余空间下限。内存和磁盘指标覆盖整个环境，不能当作编译进程的独占用量。

完成的产物先在 Linux 中校验，再导出到 Windows 的 `artifacts/运行编号`。导出通过 `.partial` 临时目录进行，复核通过后才改为正式目录。导出失败不需要重新编译：

```bash
python3 scripts/build/local.py --export-run ~/oneplus8t-kernel/runs/<运行编号>
```

若已有 `.partial` 目录，先检查残留内容，再将其移开或清理后重试。入口不会覆盖已有交付目录。

交付包含内核包或原始 Image、配置、System.map、审计记录和 provenance；启用 SUSFS 时另带用户态工具。provenance 记录真实的本地运行编号，不生成 GitHub run ID。本地产物始终按未批准候选处理。

## 云端对照

云端继续运行纯 SukiSU、SELinux hide、SUSFS extended-stat、extended-full + hide 四组合。对照必须使用同一构建提交、pins 和功能参数。下载完整功能候选的 kernel 和 tool artifact，分别放入同一目录的 `kernel`、`tool` 后运行：

```bash
python3 scripts/build/verify-artifacts.py /mnt/e/Codex\ Project/OnePlus8T-Build/artifacts/<本地运行编号> --compare <云端产物目录>
```

校验器检查交付哈希、输入指纹、Image、配置、System.map、用户态工具和 ZIP 成员内容。ZIP 容器本身可因封装时间不同而有不同哈希；核心产物或成员内容有差异时，命令失败。需要查明原因后才能记录双端等价。

正式候选的审批仍绑定云端产物、具体 PR head 和真机测试。修改共用脚本也会改变构建指纹，并要求重新构建和审批。

## 容量检查

```bash
python3 scripts/build/capacity.py
```

该命令只列出运行目录、源码、工具链和缓存占用。清理前先核对交付物、哈希、审计日志和真机测试对应关系；历史证据由维护者确认后处理。目录改名后的旧路径只会出现在保留的历史记录中。
