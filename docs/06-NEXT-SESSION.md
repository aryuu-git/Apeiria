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

## 明确未做

- 没有 fork 或修改 AstrBot 核心。
- 没有安装 NapCat，也没有创建真实部署配置。
- 没有连接 QQ、Bangumi 或 AI API。
- 没有长期运行服务；仅短暂启动隔离 AstrBot 验证插件加载后正常关停。
- 没有解压、导入或在业务代码中读取 Bangumi Archive。

## 建议的下一项工作

阶段 2 已完成。下一步进入阶段 3 的 QQ 最小链路：

1. 先建立不含账号、Token 或群号的 Windows/NapCat/OneBot 配置模板与启动检查。
2. Owner 提供一个专用测试 QQ、测试群号和管理员 QQ 号；凭据只写入 Git 忽略的本地配置。
3. 固定并记录 NapCat 版本，在本机完成反向 WebSocket 收发。
4. 验证真实事件字段、重复投递幂等、群白名单、静默控制和插件重载。

如果 Owner 直接指定其他任务，以 Owner 当前指令为准。

## 需要 Owner 后续决定

- 阶段 3 需要专用测试 QQ、测试群号和管理员 QQ 号。
- AI 服务商与群聊隐私范围可到阶段 4 再决定。

配置模板阶段不需要立即提供凭据；开始真实 QQ 联调前需要上述三个标识。

## 可直接发送给新窗口的话

```text
继续 D:\workspace\projects\Apeiria 项目。先读取项目 AGENTS.md、docs/00-CONTEXT.md 和 docs/06-NEXT-SESSION.md，核对实际状态，然后向我概括当前阶段和建议的下一项工作。暂时不要安装、运行、克隆上游或大量修改。
```

如果准备进入阶段 3，可改为：

```text
继续 D:\workspace\projects\Apeiria 项目。按项目交接规则读取最少文档，先建立不含凭据的 NapCat/OneBot Windows 部署模板与检查脚本；不要连接真实 QQ 或外部 AI。
```
