# 05 决策与未决事项

## 已确定

| 项目 | 当前结论 |
| --- | --- |
| 项目名称 | Apeiria |
| 项目位置 | `D:\workspace\projects\Apeiria` |
| 目标远程仓库 | `https://github.com/aryuu-git/Apeiria`（公开、当前为空） |
| Git 基线 | 本地仓库使用 `main` 分支，远程名为 `origin` |
| Python 基线 | Python `3.12.14`，使用 `uv 0.12.13` 管理环境与锁文件 |
| 质量工具 | `pytest`、`ruff`、严格模式 `mypy` |
| 首批题包 | 30 道；12 简单、12 普通、6 困难；来源条目对照 Bangumi Archive 验证 |
| 产品方向 | QQ 群陪伴机器人与动画轻量游戏 |
| 首个游戏 | Emoji 猜动画 |
| QQ 接入方向 | NapCatQQ + OneBot V11 |
| 固定运行内核 | AstrBot `v4.28.0`，提交 `a412146401426c0cdff8bbefb8627a03da519da8` |
| 架构原则 | 产品核心独立，框架通过薄适配层接入 |
| AstrBot 许可证 | GNU AGPL v3 或更高版本；修改或对外提供网络服务前重新审查义务 |
| AstrBot 纳入策略 | 优先采用官方固定发行版作为外部运行时，通过薄插件接入；当前不 fork |
| 插件可行性 | 首版需求从公开接口看可由插件实现，尚无修改 AstrBot 核心的已知需求 |
| 隔离验证 | 上游选定测试 160 项通过；真实插件加载成功；Apeiria 根项目 13 项测试通过 |
| 群接入安全默认 | Apeiria 插件白名单为空时拒绝所有群；OneBot 与 Dashboard 仅绑定回环地址 |
| 静默控制 | 仅配置的管理员可按群静默/恢复；阶段 3 使用进程内状态，阶段 4 持久化 |
| SQLite 状态 | schema v1 与迁移已实现；游戏进度和群静默使用同一命名空间 KV 存储 |
| Bangumi API | 默认 `https://api.bgm.tv`（本网络直连不可达，经系统代理可达）；自定义 UA；SQLite KV 缓存 TTL 7 天、间隔 1 秒；API 不可达时安静降级到过期缓存或 `None` |
| AI 陪伴 | 火山引擎 Ark OpenAI 兼容端点（`/api/coding/v3`），`deepseek-v4-flash`；上下文有限（20 条、单条 500 字）、本地 SQLite 保留 30 天；预算暂不设限 |
| 人格在场 | 每条白名单消息都进入感知与历史；本地门控（@、称呼、Owner、话题词）决定是否咨询 LLM；单次 LLM 结构化输出 `{speak, text, action}`，沉默是模型的主动选择；自主发言限频 5 次/10 分钟（@ 与 Owner 豁免）；动作通道只允许映射引擎已有表达（start_game/hint/reveal），答案判定仍由确定性状态机裁决；话题范围为擅长域加日常闲聊，敏感话题一律沉默 |
| 可观测性 | SQLite schema v2 追加事件表（默认保留 7 天，仅存被 Git 忽略的运行库）；适配层全链路打点：门控/决策/动作/游戏回复/跳过（含原因）；双通道输出 = 本地事件库 + `apeiria` logger（AstrBot 日志页实时可见） |
| 人格资料 | 扮演资产位于 Owner 维护的 `D:/PersonalHub/Bak/apeiria-roleplay`（SKILL.md + identity/voice/cognition/scenes），由 `apeiria_core.persona` 加载组装：裁去会话流程节（运行模式/按需读取/回应流程）后注入在场决策与表达层 system prompt；`persona_dir` 配置可指向其他目录，缺失时安静回退内置人格；canon-notes 属维护元数据不进 prompt |
| 管理 WebUI | 独立只读服务 `apeiria_webui`，仅绑定 `127.0.0.1:6186`；实时事件流 + 游戏状态 + 限频余量 + 配置快照（密钥掩码）；配置编辑仍走 AstrBot Dashboard（6185，保存即热重载），WebUI 不写任何数据 |
| 当前阶段 | 阶段 4 进行中；SQLite v2、Bangumi 客户端、AI 在场模型、事件流与管理 WebUI 完成；待办：跨重启验收、部署与真实群验收、题包生成接线 |
| 下一步建议 | 先完成活动题目跨 AstrBot 重启验收，再部署在场模型与 WebUI 版本并做真实群验收 |
| NapCat 固定版本 | `v4.18.19`；官方 Shell 包 SHA-256 为 `C5B7423D...ED170ACF`，真实 OneBot 链路已验证 |

## 尚未决定

1. AI 服务商、模型、预算和数据保留策略。
2. QQ 小号、测试群和管理员 ID。
3. 群聊短期上下文是否允许发送到云端 AI。
4. 默认主动程度、冷却时间和动画偏好范围。
5. 项目未来是否公开或商业化，以及由此产生的许可证策略。

## 变更方式

重要结论改变时，在本文件更新结论与理由；不要只在代码或聊天中留下隐含决定。
