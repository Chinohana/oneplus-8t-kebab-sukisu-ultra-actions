# 本地构建

维护者的内核构建、验收和发布全部在本地完成。GitHub 主仓库保存代码、历史记录和轻量检查。本地 Ubuntu 24.04 只编译完整功能版；正式发布需要该产物的审计和实际真机测试。

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

默认构建固定内核提交、SUSFS `extended-full`、SELinux hide 和 AnyKernel3 ZIP，并启用增量对象、ccache 与 ThinLTO 缓存。并行度按可用 CPU 和内存选择，最多 16；`--jobs` 可覆盖。Ubuntu 构建依赖：

```bash
sudo apt update
sudo apt install -y bc bison build-essential ccache cpio curl file flex git jq libelf-dev libssl-dev lz4 ninja-build python3 rsync unzip wget zip xz-utils
```

现有 Clang 和 Linux NDK 可直接复用。新环境先执行 `scripts/build/prepare-workspace.sh <builder-ref>`，再把固定版本的 Linux Clang 和 NDK 压缩包放入编译库的 `downloads`，执行 `scripts/build/install-toolchains.sh`。安装脚本保留下载哈希，并核对 NDK 版本；已有工具链目录需要先检查，脚本不会覆盖。

## 参数与预检

### SukiSU 五位版本号

更新依赖时，先比较 SukiSU 最新 Release 的 Manager 与最新成功 Action 的 Manager。Action 含实质 Bug 修复、功能或 UI 更新时，使用该 Action 的五位版本号；只有翻译、文档或构建流程变化时，使用最新 Release 的版本号。读取实际 APK 文件名及构建日志核实数字，并将比较范围、选择依据和源码提交记入当次同步记录。

将结果固定到 `config/build-pins.env` 的 `SUKISU_DRIVER_VERSION` 和兼容补丁中的默认版本号。编译期间不再查询远端版本。Manager 版本选择与 `SUKISU_COMMIT` 分别记录，不能把 Manager 的更新当作 builtin 驱动已同步的证据。

| 参数 | 默认值或用途 |
| --- | --- |
| `--enable-susfs`、`--enable-selinux-hide` | 固定为 `true` |
| `--profile` | 固定为 `extended-full` |
| `--use-anykernel`、`--use-ccache` | 安装包固定 `true`；ccache 默认 `true`，可关闭缓存 |
| `--kernel-source` | `approved-pin`；`latest-lineage-24.0` 核验继承关系后构建未批准候选 |
| `--jobs` | 自动选择：不超过 16、可用 CPU 数及每任务 768 MiB 的可用内存预算 |
| `--workspace` | `~/oneplus8t-kernel`，必须位于 ext4 |
| `--storage`、`--export-dir` | 编译库根目录、产物导出目录 |
| `--clang`、`--ndk` | 指定已安装的 Linux 工具链 |
| `--cache-dir` | 指定持久编译缓存目录 |
| `--object-cache-dir`、`--lto-cache-dir` | 指定增量对象和 ThinLTO 缓存，默认在工作区的 `cache/compile-objects`、`cache/thinlto` |
| `--use-incremental` | 默认 `true`；`false` 在本次独立检出中重新生成对象，仍可使用 ccache |
| `--kernel-seed`、`--sukisu-seed`、`--sm8250-seed` | 可选的本地 Git 对象种子；命中固定提交时使用 |
| `--check-only` | 只检查环境，不创建运行目录或启动编译 |
| `--minimum-free-gib` | 默认 `0`，不设置启动容量门槛；可按需指定非负 GiB 数值 |

预检不再要求剩余空间达到 50 GiB。只有显式指定 `--minimum-free-gib` 时，才按该值检查 Linux 工作区、编译库和导出位置。WSL 中显示的虚拟磁盘容量不能代替宿主存储剩余空间。内存预算用于选择启动并行度，不是运行时内存上限；可用 `--jobs` 降低并行度。

### 重复构建的缓存

每次运行仍建立独立源码快照。实际编译在受管理的 ext4 对象工作区完成，按文件内容同步源码：内容相同就保留时间戳，修改和删除的文件正常同步，编译对象由 Kbuild 的依赖检查决定是否重用。配置、基础内核提交或实际 Clang/LLD 二进制变化时，使用不同工作区。成功后，将 Image、配置、System.map 和 vmlinux 复制回本次运行目录，旧运行和证据不作修改。

每个选定配置的 ccache 上限从 800 MB 调为 4 GB；ThinLTO 缓存上限为 8 GB，只作用于原有 vmlinux.o 的 ThinLTO 链接。保留 CFI、ThinLTO、调试信息和完整功能配置。缓存首次填充仍需编译，不能把无修改检查的耗时当作首次全量构建耗时。

`audit/incremental-build.json` 记录对象工作区标识、是否已有 vmlinux、make 耗时和 Image 哈希。对象工作区是可更新缓存，不作为发布证据；发布仍以本次运行的精确源码快照、产物哈希和实际真机记录为准。不要手工编辑对象缓存中的源码，也不要把历史 `runs/` 当作可变增量工作区。

## 日志、交付和重试

运行目录为 `~/oneplus8t-kernel/runs/local-full-时间戳`。完整日志在 `audit/local-pipeline.log`，`audit/local-result.json` 记录阶段退出码、耗时，以及每 5 秒采样的 WSL 内存使用峰值、文件系统使用峰值和宿主剩余空间下限。内存和磁盘指标覆盖整个环境，不能当作编译进程的独占用量。

`audit/space-samples.jsonl` 每约 60 秒记录本次运行目录的普通文件数、目录数、符号链接数、逻辑字节数和实际分配字节数。扫描不跟随工具链、缓存等符号链接，同一硬链接内容只计一次容量。`audit/space-usage.json` 汇总运行前的文件系统用量、运行目录及各输出目录的最终占用、已有缓存的净变化，以及成功导出后的文件数与占用。运行目录采样峰值可能遗漏短时临时文件；文件系统指标每约 5 秒采样，包含同一磁盘上的其他活动。宿主空间下降还可能受到 WSL 虚拟磁盘分配方式影响，不能直接当作生成文件的大小。

完成的产物先在 Linux 中校验，再导出到 Windows 的 `artifacts/运行编号`。导出通过 `.partial` 临时目录进行，复核通过后才改为正式目录。导出失败不需要重新编译：

```bash
python3 scripts/build/local.py --export-run ~/oneplus8t-kernel/runs/<运行编号>
```

若已有 `.partial` 目录，先检查残留内容，再将其移开或清理后重试。入口不会覆盖已有交付目录。

交付包含内核包或原始 Image、配置、System.map、审计记录和 provenance；启用 SUSFS 时另带用户态工具。provenance 记录真实的本地运行编号，不生成 GitHub run ID。编译产物先按未批准候选处理；本地验收通过后才进入发布目录。

## 单一完整配置与验收

从 2026-10-27 起，维护者一律只编译和发布完整功能版。默认命令只配置、编译一个 `extended-full + SELinux hide` Image，不再编译基线、smoke、minimal-mount 或其他验收组合。SUSFS 的全部现有子选项编译为 `y`，KPM 和 kprobes 继续关闭；运行时规则和隐藏开关按实际需要设置。

产物审计保留配置、必需符号、未解析符号、链接错误、源码变更白名单和哈希检查。编译警告与 Image 大小记录在审计目录；本次没有另编基线，不再生成跨配置的警告、符号或体积增长比较。

完整配置产物通过实际手机测试后，先生成对应记录：

```bash
python3 scripts/release/local.py phone-template --artifacts <完整配置交付目录> --output <真机记录.json>
```

模板预填构建提交、运行编号、安装包和 Image 哈希，所有检查项默认 `false`。测试者填写姓名、带时区的时间，并按实际结果确认启动、ADB、root、SELinux Enforcing、SUSFS、SELinux hide、存储解密、Wi-Fi、移动网络、前后相机、指纹、音频、文件读写和内核日志。生成模板不代表已经测试，也不会操作手机。

使用构建时保存的精确检出验收：

```bash
python3 scripts/release/local.py accept --candidate <完整配置运行目录> --artifacts <完整配置交付目录> --phone-test <真机记录.json> --output <验收.json>
```

验收重新计算输入指纹，核对精确 Git 提交、pins、完整功能配置、阶段结果、交付哈希和真机记录。缺失配置项、未确认测试项、产物被改写或提交不匹配都会使验收失败。新流程无需 `--matrix`；旧参数仍可用于核对记录中同一个完整配置包。`scripts/release/matrix.py` 兼容入口也只构建一个完整配置，不会补编旧四组合。

## 生成发布目录

```bash
python3 scripts/release/local.py stage --candidate <完整配置运行目录> --artifacts <完整配置交付目录> --phone-test <真机记录.json> --acceptance <验收.json> --output <版本发布目录>
```

发布前再次核验全部证据。目录包含一个完整功能安装包、SUSFS 工具、配置、System.map、来源记录、本地验收、真机记录、完整配置摘要与 `SHA256SUMS`。摘要沿用 `matrix-summary.json` 文件名，只记录这一个配置。通过 `.partial` 目录校验后再转为正式目录，已有目录不会被覆盖。

上传 GitHub Releases 时默认也只提供这个完整功能版。单独提供安装 ZIP 和校验清单，可另附完整交付归档；归档包含同一套产物，不是另一种配置。tag 指向实际 builder commit，说明附件用途和实际完成的验证。`stage` 不会上传、创建 tag 或操作手机；发布决定不能补写真机结果。

## 需要特定配置时

需要不同功能组合，可克隆后推送到自己的 GitHub 仓库，或直接 Fork，使用手动 GitHub Actions。操作与参数见[自定义构建](CUSTOM-BUILD.md)。主仓库继续使用本地完整配置维护，自定义工作流只在使用者自己的仓库编译一个选定配置，产物是待自行验证的候选。

历史云端审批工作流仍停用。PR 的 `kernel-candidate-gate`、`kernel-runtime-policy` 和控制脚本检查不能代替本地产物验收或真机测试。

## 容量检查

```bash
python3 scripts/build/capacity.py
```

该命令只列出运行目录、源码、工具链和缓存占用。清理前先核对交付物、哈希、审计日志和真机测试对应关系；历史证据由维护者确认后处理。目录改名后的旧路径只会出现在保留的历史记录中。
