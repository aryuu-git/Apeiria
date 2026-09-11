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
- 在被忽略的 `runtime/AstrBot/` 固定 AstrBot `v4.28.0`（提交 `a412146401426c0cdff8bbefb8627a03da519da8`），未修改上游核心。
- 使用 Python 3.12.14 安装隔离运行环境；上游选定测试 160 项通过。
- 为两个领域包补充可构建的包元数据，并将固定题包作为 `anime-party` 包数据发布。
- 建立 `astrbot-plugin-apeiria` 薄适配器、插件元数据和配置 schema。
- 完成 2 项假事件适配集成测试；根项目 Ruff、严格 mypy 和 13 项 pytest 全部通过。
- 完成真实 AstrBot 启动与插件加载验证；WebUI 仅监听回环地址，验证后正常关停。阶段 2 验收完成。
- 建立不含凭据的 NapCat/OneBot 本机部署说明、示例和 PowerShell 就绪检查。
- 插件新增 fail-closed 群白名单；空列表拒绝所有群，假事件测试增至 14 项并通过。
- 核心新增管理员限定的群级静默与恢复策略；测试总数增至 17 项。
- 新增可重复运行的 AstrBot 真实事件契约检查，验证 OneBot 群事件所需字段映射。
- 控制策略新增有界消息幂等，重复静默/恢复事件不会重复回复；测试总数增至 18 项。
- Owner 已提供专用测试 QQ、测试群和管理员 ID，并已写入 Git 忽略的本地配置且通过就绪检查。
- 已从官方 Release 下载并校验 NapCat `v4.18.19` Windows 一键包；安装器无 Authenticode 签名，尚未执行。
- 官方一键包因已知 QQ 下载地址 404 未完成；改用官方 Shell 包和已安装 QQ，未修改 QQ 安装。
- NapCat `v4.18.19` 已登录专用测试 QQ，并通过带随机 Token 的本机反向 WebSocket 接入 AstrBot。
- 真实测试群已验证出题、提示、带空格答案判定、管理员静默、静默期间不回复、恢复后出题。
- NapCat WebUI、AstrBot Dashboard 和 OneBot 均仅监听回环地址；双方文件日志均关闭。阶段 3 验收完成。
- 阶段 4 已实现 SQLite schema v1、迁移与通用状态存储，并接入游戏进度和群静默。
- SQLite、引擎重建和静默策略重建测试通过；根项目当前共 22 项测试通过。
- 持久化版本已在真实 AstrBot 中启动并完成一次出题/正确答案，但活动题目跨进程恢复的真实验收尚未执行。
- 已实现 Bangumi API 客户端、SQLite TTL 缓存与安静降级，修复状态存储连接泄漏；根项目 36 项测试通过，真实网络经系统代理验证。
- 已实现 AI 陪伴领域模块与 OpenAI 兼容传输：点名/引用触发门控、有限上下文（默认 20 条、单条 500 字）、本地 SQLite 保留 30 天、安静降级；Ark coding 端点真实调用通过；根项目 50 项测试通过。

## 明确未做

- 没有 fork 或修改 AstrBot 核心。
- 没有把 NapCat、QQ 标识、Token 或真实部署配置提交到 Git。
- AI 陪伴与 Bangumi 客户端均已实现并验证端点；两者尚未部署进隔离 AstrBot，真实群验收未做。
- 当前 AstrBot 已正常关闭；NapCat Shell 仍可能保持运行和专用 QQ 登录态，但文件日志关闭。
- 没有解压、导入或在业务代码中读取 Bangumi Archive。

## 建议的下一项工作

阶段 3 已完成。下一步进入阶段 4：

1. 先运行根项目检查，并核对 SQLite 未提交代码是否与本交接一致。
2. 部署当前包到隔离 AstrBot，在测试群开始题目并获取第一层提示；重启 AstrBot 后再发“提示”，应继续为第二层。
3. 在结构化题包生成中接入已完成的 Bangumi 客户端，不读取完整 Archive 作为运行数据库。
4. 部署含 AI 陪伴的版本到隔离 AstrBot（先完成跨重启验收，再重建 wheels 部署），在测试群验收点名回复、静默优先与降级表现。
5. 接入结构化题包生成，并建立行为回归测试。

如果 Owner 直接指定其他任务，以 Owner 当前指令为准。

## 需要 Owner 后续决定

- 专用测试 QQ、测试群号和管理员 QQ 号已配置在本地忽略文件中。
- 阶段 4 需要决定 AI 服务商、模型、预算与群聊隐私范围，并提供对应 API Key。

不要在文档或仓库记录 API Key、OneBot Token、Cookie、二维码或真实聊天正文。

## 可直接发送给新窗口的话

```text
继续 D:\workspace\projects\Apeiria 项目。先读取项目 AGENTS.md、docs/00-CONTEXT.md 和 docs/06-NEXT-SESSION.md，核对实际状态，然后向我概括当前阶段和建议的下一项工作。暂时不要安装、运行、克隆上游或大量修改。
```

如果继续阶段 4，可改为：

```text
继续 D:\workspace\projects\Apeiria 项目。按项目交接规则读取最少文档，核对提交状态和 36 项测试；先完成 SQLite 活动题目跨 AstrBot 重启验收（Bangumi API 客户端与缓存已完成）。需要 AI Key 时再向我索取。
```
