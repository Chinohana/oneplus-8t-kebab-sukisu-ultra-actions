# 构建与交付规则

本项目的内核编译、配置矩阵、产物验收、真机测试确认和版本发布全部在本地执行。历史文档中的云端编译、Actions 产物审批和云端复核要求已经停用，不能作为当前操作指令。

## 当前入口

先检查 `git status --short --branch`，保留已有改动，再读 `docs/LOCAL-BUILD.md`。使用任务指定的明确提交，不因远端 main 尚未包含本地迁移工具而退回旧工作流。

本机使用 WSL2 `OnePlus8T-Build`，控制检出位于 `/home/chino/oneplus8t-kernel/control`，Windows 编译库位于 `E:\Codex Project\OnePlus8T-Build`。源码、工具链、输出和缓存位于 Linux ext4 中。

| 操作 | 本地入口 |
| --- | --- |
| 环境预检 | `python3 scripts/build/local.py --check-only` |
| 日常编译 | `python3 scripts/build/local.py`，按任务选择参数 |
| 正式配置矩阵 | `python3 scripts/release/matrix.py` |
| 真机记录、验收和发布目录 | `python3 scripts/release/local.py` |
| 容量清单 | `python3 scripts/build/capacity.py` |

各命令的完整参数见本地构建说明或 `--help`。环境或入口缺失时检查本地检出和依赖，不使用云端编译代替。

## GitHub 与验收

不通过 GitHub Actions、远端 runner 或 Action Watch 编译内核、验收产物或生成发布版本。GitHub 只承担代码管理、PR 和轻量检查；保留的手动构建、审批工作流只输出迁移说明。

正式验收必须绑定实际的本地构建快照、四组合产物、安装包与工具哈希和真机记录。不能用旧 GitHub run、bot 评论、通过的 PR 检查或未填写的测试模板代替。

文档、Agent 规则和发布辅助工具的修改不自动触发内核重编译。构建输入改变或任务要求验证构建时，再运行相应本地配置。上传文件、创建 Release、刷写设备和切槽按当次用户授权执行。

## 文档和历史

文档及 PR 说明使用 Sepia。`docs/README.md` 区分当前手册和历史记录；移植文档、旧分支、运行快照与来源记录用于追溯，不作为当前构建步骤。不要为了更新说明而改写历史日志、哈希和审批证据。

## 子代理模型偏好

- 需要使用子代理时，默认选择 GPT-6 Luna，思考强度设为 max。
- 如果子代理任务特别复杂，或者子代理负责最终审查，选择适合该任务的更强模型。
