# 04 上游复用策略

## 基本原则

成熟复用不是复制快照后任意修改，而是保留来源、历史、许可证和升级路径。

## AstrBot

- 初期固定一个验证过的版本，优先不修改核心。
- Apeiria 业务能力优先放在独立核心和插件中。
- 确需修改时，建立自己的 fork：`origin` 指向自有 fork，`upstream` 指向官方仓库。
- 每个上游补丁记录原因、影响范围、测试和可能的替代扩展点。
- 合并上游更新前执行集成与对话回归测试。

## AstrBot 静态评估（2026-09-11）

### 上游与版本

- 官方仓库：<https://github.com/AstrBotDevs/AstrBot>。
- 官方许可证文件声明 AstrBot 使用 GNU AGPL v3 或更高版本：<https://github.com/AstrBotDevs/AstrBot/blob/master/LICENSE>。
- 评估时最新正式发行版为 `v4.28.0`（2026-09-08，提交 `a412146`）：<https://github.com/AstrBotDevs/AstrBot/releases/tag/v4.28.0>。
- `v4.28.0` 的发行说明警告配置结构发生优化，升级后再降级可能重置部分配置；回滚时必须连同配置备份恢复。
- 官方源码部署文档要求 Python `>=3.12`，并推荐 `uv`：<https://docs.astrbot.app/deploy/astrbot/cli.html>。

### 隔离验证结果（2026-09-11）

- 固定版本：`v4.28.0`，完整提交 `a412146401426c0cdff8bbefb8627a03da519da8`。
- 环境：Python `3.12.14`，AstrBot 独立虚拟环境位于被 Git 忽略的 `runtime/AstrBot/.venv/`。
- 上游选定测试：160 项通过，仅有 1 项上游弃用警告。
- Apeiria 的两个领域包均能构建为 wheel；动画题包包含在 `anime-party` wheel 中。
- 插件元数据和 `_conf_schema.json` 可被 AstrBot 解析；真实启动时成功加载 `astrbot_plugin_apeiria 0.1.0`。
- 插件通过公开事件接口调用领域核心；假事件覆盖已处理与忽略消息，根项目共 13 项测试通过。
- WebUI 验证时只监听 `127.0.0.1:6185`，服务随后正常关停；没有连接 QQ 或配置 AI。
- 未修改 AstrBot 核心，因此当前不建立 fork。

### 公开扩展能力

| Apeiria 首版需求 | AstrBot 公开扩展点 | 初步判断 |
| --- | --- | --- |
| 接收群聊、私聊、指令和普通消息 | `AstrMessageEvent`、指令与事件类型/平台过滤器 | 插件可实现 |
| 识别群、用户和平台 | `unified_msg_origin`、`session`、发送者信息 | 插件可映射为领域事件 |
| 被点名、引用或明确询问时响应 | 消息对象、`is_at_or_wake_command`、事件过滤与优先级 | 插件可实现；自然语言判断留在核心策略 |
| 开始、作答、提示、揭晓、再来和暂停 | 指令/普通消息监听；可选会话控制器 | 游戏状态机应放在 `anime-party`，插件只转发事件 |
| 以整个群为游戏会话 | 会话控制器支持自定义会话 ID；也可直接按 UMO 管理 | 可实现；优先由领域核心按 UMO 建模，避免绑定框架控制器 |
| 被动与主动发送消息 | `yield event.*_result`、`event.send()`、`Context.send_message()` | 插件可实现 |
| 群白名单、静默和 LLM 开关 | 配置文件白名单、自定义规则、插件配置 | 可实现；领域层仍需独立静默状态 |
| 插件可视化配置 | `_conf_schema.json` 自动生成 WebUI 配置 | 插件可实现 |
| 复杂管理页面 | 插件 Pages + `astrbot.api.web`，受限 iframe | 可选能力；第一版不需要 |
| 少量插件状态 | 插件级异步 KV 存储 | 可用于适配器元数据，不承载主要领域数据库 |
| 游戏状态与题库 | 插件数据目录允许自有文件；Apeiria 计划使用 SQLite | 由独立领域模块负责，不依赖 AstrBot KV |
| NapCatQQ 接入 | 官方支持 OneBot v11 反向 WebSocket，并列出 NapCat | 无需修改核心 |

相关官方文档：

- 插件开发：<https://docs.astrbot.app/dev/star/plugin-new.html>
- 消息事件：<https://docs.astrbot.app/dev/star/guides/listen-message-event.html>
- 发送消息：<https://docs.astrbot.app/dev/star/guides/send-message.html>
- 插件配置：<https://docs.astrbot.app/dev/star/guides/plugin-config.html>
- 插件存储：<https://docs.astrbot.app/dev/star/guides/storage.html>
- 会话控制：<https://docs.astrbot.app/dev/star/guides/session-control.html>
- 插件 Pages：<https://docs.astrbot.app/dev/star/guides/plugin-pages.html>
- OneBot v11：<https://docs.astrbot.app/platform/aiocqhttp.html>

### 结论与边界

- 第一阶段需求从公开接口看可以完全通过插件适配，不存在已知的 AstrBot 核心补丁需求。
- 推荐采用“官方固定发行版作为外部运行时 + 独立 Apeiria 包 + 薄插件”，暂不建立 fork。
- 不把 AstrBot 源码复制进自研包，也不让领域模型引用 `AstrMessageEvent`、UMO 字符串格式或 AstrBot 存储对象。
- 插件配置适合管理员参数；游戏状态、幂等键、题包与未来迁移仍由 Apeiria 自己的存储接口管理。
- AstrBot 的 AGPL 许可证不会因为单纯内部运行就自动要求把所有独立代码公开，但修改、组合、分发和网络交互的具体边界需要按实际发布方式重新审查；本记录不是法律意见。

### 固定版本前的验证门

固定版本验证门已通过。真实 OneBot 字段、插件热重载和部署回滚仍在阶段 3 的 NapCat 测试链路中验证。

## NapCatQQ

- 作为独立 QQ 协议组件运行，不默认复制或修改源码。
- 固定经过验证的版本，记录安装来源、配置和回滚方式。
- OneBot 与管理界面仅监听受控地址，不公开暴露。

## 数据与其他依赖

- Bangumi API 是外部服务；Archive 是可重新获取的数据，不属于源码。
- 不同时纳入多个候选机器人框架。
- 第三方许可证、NOTICE、版本和修改说明统一记录在 `third-party`。

## 当前边界

AstrBot 仅克隆并安装在被忽略的隔离运行目录；未 fork、未修改核心、未作为源码提交。
