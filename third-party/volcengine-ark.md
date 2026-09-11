# 火山引擎 Ark 来源记录

- 控制台与文档：<https://www.volcengine.com/product/ark>
- 接入协议：OpenAI 兼容 Chat Completions
- Base URL（2026-09-12 实测）：`https://ark.cn-beijing.volces.com/api/coding/v3`
  - 注意：coding 专用端点必须带 `/v3`，`/api/coding/chat/completions` 返回 404
- 模型：`deepseek-v4-flash`
- 接入代码：`packages/apeiria-core/src/apeiria_core/companion.py`（`OpenAICompatibleTransport`）
- 验证脚本：`packages/apeiria-core/scripts/verify_llm_api.py`

## 当前状态

2026-09-12 真实验证：经本地 urllib 传输（默认走系统代理配置）调用 chat completions 返回正常回复。传输层带 30 秒超时；失败时由 `CompanionService` 安静降级为不回复。

## 安全边界

- API Key 只存放在 Git 忽略的 `deploy/napcat/apeiria.local.json` 与 AstrBot 运行时插件配置中；不入仓库、文档或日志。
- Key 曾出现在与 Owner 的对话记录中，建议 Owner 在阶段验收后轮换。
- 发送到云端的内容仅限：系统人格提示 + 最近有限条群聊文本（默认 20 条，单条截断 500 字符）；不发送图片、CQ 码或数据库原文。
