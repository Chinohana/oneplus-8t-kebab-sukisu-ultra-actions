# 本地构建

内核构建、配置矩阵、验收和发布全部在本地完成。GitHub 只保存代码、历史记录和轻量检查。日常试编译在本地 Ubuntu 24.04 中运行；正式发布还需要本地矩阵及实际产物的真机测试。

源码、工具链和编译缓存放在 Linux ext4 文件系统中，默认工作目录为 `~/oneplus8t-kernel`。交付物默认导出到 `~/oneplus8t-build/artifacts`，也可通过 `--storage` 和 `--export-dir` 指定其他位置。

## 选择构建提交

Windows 项目中的 `repo-local` 用于修改和提交控制代码，WSL 中的 `control` 用于运行已提交的版本。先把修改提交到分支，再在专用 Ubuntu 中取回明确的提交。工作树有未提交文件时，入口会退出。

```bash
cd ~/oneplus8t-kernel/control
git fetch origin main
git checkout --detach FETCH_HEAD
python3 scripts/build/local.py --check-only
python3 scripts/build/local.py
```

后续构建可将示例分支替换为已审查的分支或提交。每次运行会创建独立检出，运行中的脚本不受外部入口文件修改影响。源码、补丁和工具链版本来自该提交的 pins。

默认构建固定内核提交、SUSFS `extended-full`、SELinux hide 和 AnyKernel3 ZIP，并启用 ccache，使用 8 个并行任务。Ubuntu 构建依赖：

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
| `--kernel-seed`、`--sukisu-seed`、`--sm8250-seed` | 可选的本地 Git 对象种子；命中固定提交时使用 |
| `--check-only` | 只检查环境，不创建运行目录或启动编译 |
| `--minimum-free-gib` | 默认 `0`，不设置启动容量门槛；可按需指定非负 GiB 数值 |

预检不再要求剩余空间达到 50 GiB。只有显式指定 `--minimum-free-gib` 时，才按该值检查 Linux 工作区、编译库和导出位置。WSL 中显示的虚拟磁盘容量不能代替宿主存储剩余空间。并行度先保持 `8`，再根据实际内存和耗时调整。

## 日志、交付和重试

运行目录为 `~/oneplus8t-kernel/runs/local-full-时间戳`。完整日志在 `audit/local-pipeline.log`，`audit/local-result.json` 记录阶段退出码、耗时，以及每 5 秒采样的 WSL 内存使用峰值、文件系统使用峰值和宿主剩余空间下限。内存和磁盘指标覆盖整个环境，不能当作编译进程的独占用量。

`audit/space-samples.jsonl` 每约 60 秒记录本次运行目录的普通文件数、目录数、符号链接数、逻辑字节数和实际分配字节数。扫描不跟随工具链、缓存等符号链接，同一硬链接内容只计一次容量。`audit/space-usage.json` 汇总运行前的文件系统用量、运行目录及各输出目录的最终占用、已有缓存的净变化，以及成功导出后的文件数与占用。运行目录采样峰值可能遗漏短时临时文件；文件系统指标每约 5 秒采样，包含同一磁盘上的其他活动。宿主空间下降还可能受到 WSL 虚拟磁盘分配方式影响，不能直接当作生成文件的大小。

完成的产物先在 Linux 中校验，再导出到 Windows 的 `artifacts/运行编号`。导出通过 `.partial` 临时目录进行，复核通过后才改为正式目录。导出失败不需要重新编译：

```bash
python3 scripts/build/local.py --export-run ~/oneplus8t-kernel/runs/<运行编号>
```

若已有 `.partial` 目录，先检查残留内容，再将其移开或清理后重试。入口不会覆盖已有交付目录。

交付包含内核包或原始 Image、配置、System.map、审计记录和 provenance；启用 SUSFS 时另带用户态工具。provenance 记录真实的本地运行编号，不生成 GitHub run ID。编译产物先按未批准候选处理；本地验收通过后才进入发布目录。

## 本地矩阵与验收

日常修改只编译需要的配置。准备发布时，在干净的构建提交上执行四组合矩阵：

```bash
python3 scripts/release/matrix.py --check-only
python3 scripts/release/matrix.py --output ~/oneplus8t-kernel/audit/matrix-<版本>.json
```

矩阵按顺序构建纯 SukiSU、SELinux hide、SUSFS extended-stat 和 extended-full + hide，共享本地 ccache。每个组合保存独立交付；任何一个失败，矩阵都不能用于验收。矩阵文件只引用已完成的本地产物，不能用云端结果替代。

完整配置产物通过实际手机测试后，先生成对应的记录表：

```bash
python3 scripts/release/local.py phone-template --artifacts <完整配置交付目录> --output <真机记录.json>
```

模板预填构建提交、运行编号、安装包和 Image 哈希，所有检查项默认为 `false`。由测试者填写姓名、带时区的测试时间，并按实际结果逐项确认启动、ADB、root、SELinux Enforcing、SUSFS、SELinux hide、存储解密、Wi-Fi、移动网络、前后相机、指纹、音频、文件读写及内核日志。生成模板不代表已经测试，也不会操作手机。

使用构建时保存的精确检出完成验收：

```bash
python3 scripts/release/local.py accept --candidate <完整配置运行目录> --artifacts <完整配置交付目录> --matrix <矩阵.json> --phone-test <真机记录.json> --output <验收.json>
```

验收工具重新计算各组合的指纹，核对 Git 提交、pins、完整审计阶段、交付哈希和真机记录。完整配置包必须是矩阵中的同一个包。缺少组合、未完成的测试项、被改写的产物或不匹配的提交都会使验收失败。验收记录只写入本地，不依赖 Actions run、bot 评论或 GitHub 的审批工作流。

## 生成发布目录

```bash
python3 scripts/release/local.py stage --candidate <完整配置运行目录> --artifacts <完整配置交付目录> --matrix <矩阵.json> --phone-test <真机记录.json> --acceptance <验收.json> --output <版本发布目录>
```

生成发布目录前会再次核验全部证据，并确认验收记录仍与当前文件一致。目录包含安装包、SUSFS 用户态工具、配置、System.map、来源记录、本地验收及真机记录、去除本地路径的矩阵摘要和 `SHA256SUMS`。通过 `.partial` 临时目录校验后才转为正式目录，已有目录不会被覆盖。

该目录就是本地版本交付。将来如需上传到 GitHub Releases，可以从本地上传已验收文件；上传不再触发云端编译或复验。当前命令不会上传、创建 tag 或操作手机。

原 Actions 编译、云端审批和构建结果通知入口已停用。PR 的 `kernel-candidate-gate` 与 `kernel-runtime-policy` 保留原检查名称，输出本地验收说明，不能作为任何产物的验收凭据。

## 容量检查

```bash
python3 scripts/build/capacity.py
```

该命令只列出运行目录、源码、工具链和缓存占用。清理前先核对交付物、哈希、审计日志和真机测试对应关系；历史证据由维护者确认后处理。目录改名后的旧路径只会出现在保留的历史记录中。
