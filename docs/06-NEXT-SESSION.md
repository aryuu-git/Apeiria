# 06 下一会话交接

## 新窗口启动协议

新会话进入 `D:\workspace\projects\Apeiria` 后：

1. 读取根目录 `AGENTS.md`。
2. 读取 `docs/00-CONTEXT.md` 和本文件。
3. 用只读方式核对一级目录和文件状态。
4. 根据 Owner 的新指令，只读取对应的最少编号文档。
5. 继续现有方向，不重新做完整需求访谈。

## 已完成

- 创建项目根目录 `D:\workspace\projects\Apeiria`。
- 确立 Apeiria 为完整产品，AstrBot 为当前首选、可替换的运行内核。
- 确立 NapCatQQ + OneBot V11 为 QQ 接入方向。
- 确立独立领域核心、动画游戏模块和 AstrBot 薄适配层的边界。
- 创建 `runtime`、`packages`、`persona`、`deploy`、`tests`、`data` 和 `third-party` 骨架目录。
- 创建 `00` 至 `06` 的渐进式开发文档。
- 完成 AstrBot 官方仓库、许可证、发布版和公开插件扩展点的静态评估。
- 初步确认首版需求可通过薄插件接入，无已知核心补丁需求。
- 决定优先采用官方固定发行版作为外部运行时，暂不 fork；`v4.28.0` 仅为待验证候选。
- 确认目标远程仓库为 `https://github.com/aryuu-git/Apeiria`；初始化前仓库公开且为空。
- 初始化本地 Git，以 `main` 为初始分支，并将目标仓库配置为 `origin`。
- 下载并校验 Bangumi Archive `dump-2026-09-08.210336Z.zip`；原始归档位于被 Git 忽略的 `data/bangumi/archive/`，来源记录见 `third-party/bangumi-archive.md`。
- 建立 Python 3.12.14 + `uv` 工程环境，配置 `pytest`、`ruff` 和严格模式 `mypy`。
- 建立平台无关消息模型、Bangumi Archive 流式候选筛选器和 Emoji 游戏状态机。
- 建立 30 道固定题包（12 简单、12 普通、6 困难），全部对照快照验证。
- 单元测试覆盖答案归一化、别名、游戏流程、难度、暂停、重复消息和数据筛选。
- 将领域回复结果与简体中文表达层分离，新增三组群聊行为回归样例。
- 补充群会话隔离、提示边界、重复揭晓和幂等缓存容量测试；阶段 1 验收完成。

## 明确未做

- 没有克隆、fork 或安装 AstrBot。
- 没有安装 Python、AstrBot、NapCat 或其他依赖。
- 没有创建数据库或真实部署配置。
- 没有连接 QQ、Bangumi 或 AI API。
- 没有运行测试或启动服务。
- 没有解压、导入或在业务代码中读取 Bangumi Archive。

## 建议的下一项工作

阶段 1 已完成。下一步需 Owner 明确授权进入阶段 2：

1. 在隔离目录引入 AstrBot `v4.28.0`，记录确切来源与提交，不修改其核心。
2. 验证 Python 3.12、最小本地插件加载、配置、重载、数据目录和消息事件字段。
3. 验证通过后将 `v4.28.0` 固定为运行时基线。
4. 建立 `astrbot-plugin-apeiria` 薄适配器，并用假事件完成集成测试。

如果 Owner 直接指定其他任务，以 Owner 当前指令为准。

## 需要 Owner 后续决定

- 是否授权后续在隔离环境引入并验证 AstrBot `v4.28.0`。
- AI 服务商、隐私范围、QQ 小号和测试群。

当前阶段不需要决定 AI 服务商、QQ 身份和测试群。

## 可直接发送给新窗口的话

```text
继续 D:\workspace\projects\Apeiria 项目。先读取项目 AGENTS.md、docs/00-CONTEXT.md 和 docs/06-NEXT-SESSION.md，核对实际状态，然后向我概括当前阶段和建议的下一项工作。暂时不要安装、运行、克隆上游或大量修改。
```

如果准备进入阶段 1，可改为：

```text
继续 D:\workspace\projects\Apeiria 项目。按项目交接规则读取最少文档，然后与我确认 Git、Python 和依赖管理方案，再建立离线领域核心与 Emoji 游戏状态机；先不要接入 AstrBot、NapCat、QQ 或外部 API。
```
