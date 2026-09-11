# Apeiria 项目协作规则

本文件适用于 `D:\workspace\projects\Apeiria` 及其全部子目录。用户当前指令、更深层目录中的 `AGENTS.md` 和更高优先级规则优先。

## 项目目标

Apeiria 是面向熟人 QQ 群的长期陪伴机器人。它以艾佩理雅启发的原创人格自然参与群聊，并提供 Emoji 猜动画等轻量游戏。

当前架构方向是：以 AstrBot 作为可替换的运行内核，通过独立领域核心和适配层实现产品能力；QQ 接入使用 NapCatQQ 与 OneBot V11。

## 会话开始与渐进阅读

处理本项目任务时：

1. 先读取本文件。
2. 再读取 `docs/00-CONTEXT.md` 与当前任务对应的最少文档。
3. 不要为了熟悉项目一次性读取所有资料、下载大型数据或拉取所有上游源码。
4. 文档与实际目录冲突时，以实际状态为准，并更新相关决策记录。

文档路由：

- 产品范围与体验：`docs/01-PRODUCT.md`
- 系统边界与目录：`docs/02-ARCHITECTURE.md`
- 分阶段实施：`docs/03-ROADMAP.md`
- 上游复用与修改：`docs/04-UPSTREAM.md`
- 已决定与未决定事项：`docs/05-DECISIONS.md`
- 新窗口接续工作：`docs/06-NEXT-SESSION.md`

## 工程边界

- `runtime/`：第三方运行内核或其受控 fork，不承载 Apeiria 领域逻辑。
- `packages/apeiria-core/`：人格、回复决策、会话边界等平台无关核心。
- `packages/anime-party/`：动画游戏、题包、答案判定和 Bangumi 数据能力。
- `packages/astrbot-plugin-apeiria/`：AstrBot 事件与 Apeiria 核心之间的薄适配层。
- `persona/`：可部署的人格规则、参数与回归样例。
- `deploy/`：NapCat 和 Windows 部署材料。
- `tests/`：单元、集成和对话行为测试。
- `data/`：本地数据库、缓存和外部数据；运行数据默认不提交。
- `third-party/`：第三方许可证、版本与来源记录。

## 实现原则

- 状态机优先于 AI；当前题目的答案、提示和进度不得由自由对话临时改变。
- AI 负责理解与表达，不作为动画事实的唯一来源。
- 核心领域逻辑不得直接依赖 AstrBot 内部对象。
- 优先通过公开扩展点集成；确需修改上游时，保持补丁小、可解释、可测试。
- 配置、密钥、运行数据与源码分离；不得提交 Token、Cookie、API Key 或真实群聊正文。
- 默认不永久保存完整聊天历史，并为静默、暂停和数据清理保留明确能力。
- 外部消息按可能重复投递设计，避免重复回复、重复发题和重复计分。

## 修改约束

- 未经 Owner 明确要求，不执行 Git commit、push、发布或公网部署。
- 未经当前任务需要，不下载 Bangumi Archive、不采购或配置服务器、不开放公网端口。
- 引入第三方项目必须保留 Git 历史或明确版本来源，同时记录许可证。
- 不把候选框架全部复制进项目；只纳入已经决定使用的组件。
- 修改架构、范围或上游策略时，同步更新 `docs/05-DECISIONS.md`。

## 当前阶段

目前只搭建项目与文档骨架。不要自行安装依赖、拉取 AstrBot、连接 QQ、创建数据库或尝试运行，除非 Owner 后续明确要求进入相应阶段。

新会话若收到“继续 Apeiria 项目”之类的指令，先读 `docs/00-CONTEXT.md` 和 `docs/06-NEXT-SESSION.md`，核对实际文件状态，再与 Owner 对齐下一项工作。不要重新进行已经完成的项目定位讨论。
