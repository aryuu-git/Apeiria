# AstrBot 来源记录

- 官方仓库：<https://github.com/AstrBotDevs/AstrBot>
- 固定版本：`v4.28.0`
- 固定提交：`a412146401426c0cdff8bbefb8627a03da519da8`
- 许可证：GNU AGPL v3 或更高版本（以固定版本仓库中的 `LICENSE` 为准）
- 本地位置：`runtime/AstrBot/`（被 Git 忽略，不作为 Apeiria 源码提交）
- Python：`3.12.14`
- 引入日期：2026-09-11

## 使用方式

Apeiria 通过公开插件接口接入 AstrBot，领域逻辑位于独立包中。当前未修改 AstrBot 核心，也未建立 fork。

## 验证记录

- 上游选定测试：160 项通过，1 项上游弃用警告。
- 插件元数据与配置 schema 可由 AstrBot 解析。
- `astrbot_plugin_apeiria 0.1.0` 在真实 AstrBot 启动中加载成功。
- WebUI 仅绑定回环地址，验证后服务已正常关停。

## 升级与回滚

升级前固定新提交并重跑上游选定测试、Apeiria 集成测试和真实加载验证。由于 `v4.28.0` 的配置迁移可能不支持安全降级，回滚运行时版本时应同时恢复对应配置和运行数据备份。
