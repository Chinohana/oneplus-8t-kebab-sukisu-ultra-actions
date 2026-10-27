# 2026-10-28：41095 安装包解包失败

41095 候选在 LineageOS Recovery 24.0 中安装失败。照片显示签名提示后已进入 AnyKernel3，完成设备检查并读取 `boot_a`，随后报 `Splitting image failed. Aborting...`。这次中止发生在解包阶段，尚未进入 `flash_boot`。

固定的 AnyKernel3 `08e9d1281f38019efcf8818e18525e55e679046f` 中，`magiskboot unpack` 后新增了 `[ $? == 1 ] && splitfail=1`。解包成功返回 0 时，该条件表达式返回 1；随后的 `$? != 0` 因此触发中止。这是安装脚本对成功结果的误判。

本地回归直接执行旧包中的 `split_boot` 函数，用普通临时文件模拟分区、模拟解包器返回成功，复现同一句错误。修复将该表达式改为 `case`，保留原有对返回码 1 的失败处理及返回码 2 的兼容处理。测试覆盖成功、解包失败、返回码 2 和输出管道失败；只修改判断状态，不移除失败检查。

后续构建在打包阶段应用 `patches/anykernel3-split-status.patch`，并对实际将要打包的安装函数运行回归测试。补丁不匹配时停止打包。

## 修复已有候选

`scripts/repackage-anykernel.py` 从原 ZIP 生成新文件，要求提供已审计的 Image 哈希。它检查 Image、应用同一补丁、运行四项安装函数测试，再逐一核对 ZIP 内容。只有 `tools/ak3-core.sh` 可以改变；Image、设备检查、分区与槽位选择、打包工具和其余内容必须与旧包一致。原文件和历史构建记录保留。

```bash
python3 scripts/repackage-anykernel.py \
  --source /path/to/original.zip \
  --output /path/to/new_AK3fix.zip \
  --expected-image-sha256 f33876485b3a6b5dddc3916e7af5a975d498d5d316af4074e4a1e4609d156a4b
```

新 ZIP 旁的 `.sha256` 与 `.repair.json` 记录原包哈希、修复提交、Image 哈希、唯一变化的成员和测试结果。此操作只重新打包，不重新编译内核，不生成新的完整构建或真机验收记录。本次尚未在手机上重试安装。
