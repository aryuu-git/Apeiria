# Apeiria

Apeiria 是一个面向熟人 QQ 群（约 6 人）的长期陪伴机器人：以《景之海的艾佩莉亚》中艾佩理雅启发的原创人格在群里"在场"——听每一条消息、自主决定何时开口、自然接话与吐槽，并主持 Emoji 猜动画游戏。运行内核是 AstrBot（可替换），QQ 接入使用 NapCatQQ + OneBot V11。

> 角色扮演声明：Apeiria 是原创人格演绎，不冒充官方角色，也不声称拥有真实意识。

## 当前现状（2026-09-12，阶段 4）

已上线并在真实测试群验收过的能力：

- **Emoji 猜动画游戏**：30 道人工校验题包（12 简单 / 12 普通 / 6 困难），三层提示、答案归一化（含别名、空格）、暂停/难度切换、防重复投递；**答案判定与进度由确定性状态机裁决，LLM 不得干预**。
- **在场模型（人格化交互）**：每条白名单群消息进入感知与记忆；本地注意力门控（@、称呼、Owner、话题词）决定是否咨询 LLM；单次 LLM 调用输出结构化决策 `{speak, text, action}`——沉默是她自己的选择；`action` 通道允许她主动出题（仍由状态机执行）。
- **Owner 偏向**：`owner_ids` 与管理员权限分离；Owner 消息必达决策层、不受自主发言限频约束、上下文中带 Owner 标记。
- **表达层**：游戏回复的措辞全部经 LLM 生成（full 整句 / lead 引子+固定信息行拼接）；表达上下文按 kind 裁剪——错答与提示不向模型提供答案名，机制性防剧透；LLM 失败自动回退模板池。
- **点名与限频**：名字呼叫（含游戏进行中）永不判答案、必获回应（重试 + 兜底短语）；自主发言限频 5 次/10 分钟（@ 与 Owner 豁免）；单局超时（默认 15 分钟）自动揭晓。
- **人格资料库**：`apeiria_core.persona` 从 Owner 维护的扮演技能目录（SKILL.md + references）加载裁剪组装 system prompt，注入决策与表达层；目录缺失回退内置人格。
- **Bangumi API 客户端**：默认 `api.bgm.tv`（含 UA 规范、TTL 缓存 7 天、限速、安静降级），已真实验证；尚未接入题包生成。
- **可观测性**：SQLite schema v2 事件表（默认保留 7 天）+ 全链路打点（门控/决策/动作/游戏回复/跳过含原因），双通道输出到本地事件库与运行日志。
- **管理 WebUI**（`http://127.0.0.1:6186`，只读）：实时事件流、游戏状态、限频余量、配置快照（密钥掩码）。配置编辑走 AstrBot Dashboard（`http://127.0.0.1:6185`），保存即热重载。

尚未完成：结构化题包生成接入 Bangumi 客户端；阶段 5 长期运行（Windows 常驻、健康检查、备份）。

## 架构

```text
QQ + NapCatQQ (v4.18.19)
      ↓ OneBot V11 反向 WebSocket (127.0.0.1:6199)
AstrBot 运行内核 (v4.28.0, 隔离于 runtime/，未改核心)
      ↓ astrbot-plugin-apeiria 薄适配层
Apeiria 领域核心（apeiria-core）          游戏状态机（anime-party）
  · 注意力门控 / 在场决策                  · Emoji 出题 / 答案判定（确定性）
  · 有限上下文记忆（SQLite, 30 天）        · 题包与提示层级
  · OpenAI 兼容传输（火山引擎 Ark）        · Bangumi API 客户端与缓存
      ↓
SQLite (runtime 忽略目录, schema v2: state + events)
      ↓
管理 WebUI（127.0.0.1:6186, 只读）
```

## 本地运行

环境：Windows、Python 3.12.14、uv；AstrBot 与 NapCat 已固定在 `runtime/`（Git 忽略）。

```powershell
uv sync                      # 安装工作区与开发工具
uv run ruff check .          # lint
uv run mypy                  # 严格类型检查
uv run pytest -q             # 单元 + 集成测试
```

联调拓扑与凭据约定见 [deploy/napcat/README.md](deploy/napcat/README.md)；真实链路启动：

1. NapCat（专用测试 QQ）反向 WS 连接 `ws://127.0.0.1:6199/ws`。
2. AstrBot：`uv run main.py`（在 `runtime/AstrBot/`），Dashboard 仅绑定 127.0.0.1:6185。
3. 管理台：`uv run python -m apeiria_webui`，仅绑定 127.0.0.1:6186。
4. 端点验证脚本：`packages/apeiria-core/scripts/verify_llm_api.py`、`packages/anime-party/scripts/verify_bangumi_api.py`。

## 配置与密钥

- 插件配置存于 AstrBot 运行时（`data/config/astrbot_plugin_apeiria_config.json`），Dashboard 可视化编辑；schema 见 `packages/astrbot-plugin-apeiria/_conf_schema.json`。
- 真实凭据（QQ、测试群、OneBot Token、Ark API Key）只存在于 Git 忽略的本地文件（`deploy/napcat/apeiria.local.json`、runtime 配置），不入仓库、不入文档。
- AI 故障一律安静降级：LLM 不可达时游戏照常、在场层保持沉默，绝不刷错误消息。

## 交接

- 新会话入口：[docs/00-CONTEXT.md](docs/00-CONTEXT.md) 与 [docs/06-NEXT-SESSION.md](docs/06-NEXT-SESSION.md)（当前进度、待办、可直接使用的启动语）。
- 决策记录：[docs/05-DECISIONS.md](docs/05-DECISIONS.md)；上游与来源：[third-party/](third-party/)。
- 已知待办：结构化题包生成接入 Bangumi 客户端；阶段 5 长期运行；Ark API Key 轮换。
