# 2026-10-28 上游同步

本次更新两个固定输入：SukiSU builtin 从 `0b666cad90f3a13cb4085f8c88e5144594e82030` 更新到 `b59170724cdc05bf5dee8d8a8b182c5f1ddd60e3`，AnyKernel3 从 `08e9d1281f38019efcf8818e18525e55e679046f` 更新到 `41f04bdb4ee30a44e429c2c1131d5e8bb32b15f1`。内核、SUSFS 参考、Clang 和 NDK 保持原 pin。

## builtin 扩展 ABI

[builtin 新增提交](https://github.com/SukiSU-Ultra/SukiSU-Ultra/commit/b59170724cdc05bf5dee8d8a8b182c5f1ddd60e3) 发布 STICKY、PERSIST、PER_UID、REBOOT 能力位，增加扩展 ABI 探测和处理器注册校验。原 ioctl 结构仍为 32 字节；旧 reserved 字段改为 api_version，旧客户端传入 0 时按 ABI 1 处理。

本地兼容补丁仍可应用。新增宿主测试直接编译固定源码中的版本判断、能力校验、GET 和探测分发函数，核对结构大小及字段偏移，覆盖旧客户端、较新客户端、错误能力组合、过高最低 ABI、未知扩展、读取失败和空指针。完整构建的 hook 审计会在实际源码上执行这项测试。

## Manager 与五位版本号

最新 Release 仍是 [v4.2.1-r2 / 41068](https://github.com/SukiSU-Ultra/SukiSU-Ultra/releases/tag/v4.2.1-r2)。最新成功的 [Build Manager 40585558597](https://github.com/SukiSU-Ultra/SukiSU-Ultra/actions/runs/40585558597) 对应 main `080ba098902c1ea8f09748536f9d920329e2f7ce`，实际下载文件为 `SukiSU_v4.2.1-r2_41097-release.apk`。determine-version 日志确认 main 提交数 3912，计算为 `40000 + 3912 - 2815 = 41097`。

[41095 Action 到本次 Action](https://github.com/SukiSU-Ultra/SukiSU-Ultra/compare/96ceb4a42c50e27199a094264f62cfbafee77fa0...080ba098902c1ea8f09748536f9d920329e2f7ce) 新增扩展能力与 ABI 信息，以及由内核处理器表驱动的扩展页面。这属于实际功能和 UI 更新；加上此前相对 Release 的修复，符合选用 Action 版本的规则。因此驱动版本与默认值均固定为 **41097**。

Manager APK SHA-256：`c13f4884b47e6648fb116ed49647eaa544ee54d6c30467b933164bdccf25aa5e`。Manager main 已包含 ABI 2 的枚举页面，builtin 本次仅包含 ABI 1 的能力发布；这两个分支分别记录，不能声称本次 builtin 已具备 main 的全部扩展枚举接口。

## AnyKernel3 原生修复

[上游修复 41f04bd](https://github.com/osm0sis/AnyKernel3/commit/41f04bdb4ee30a44e429c2c1131d5e8bb32b15f1) 将导致成功解包误报失败的条件表达式改回 case，与本项目 41095 AK3fix 的修复相同。打包阶段不再重复应用本地补丁，继续在实际安装函数上运行成功、失败、返回码 2 和管道失败四项测试。

旧的 `patches/anykernel3-split-status.patch` 留给 41095 历史修复包的证据核验和重新打包使用，不再应用于新的 AnyKernel3 pin。旧发布和验收记录保留原样。

## 本地验证

扩展 ABI 宿主测试与上游安装函数四项测试已通过。下一步只构建 SUSFS extended-full + SELinux hide 一个完整配置；完整构建、审计与导出结果完成后补记。本次候选尚未进行真机验收，也未发布；正式下载仍为已验收的 41095。
