# 00 项目上下文

## 一句话目标

为约 6 人的熟人动画爱好者 QQ 群构建一个长期存在、有分寸的艾佩理雅陪伴机器人，并以 Emoji 猜动画作为首个游戏闭环。

## 当前状态

- 已建立项目目录和文档骨架。
- 已建立项目级 `AGENTS.md`，其中包含渐进阅读、工程边界和修改约束。
- 已初始化本地 Git，初始分支为 `main`，远程为 `https://github.com/aryuu-git/Apeiria`。
- 已将 AstrBot `v4.28.0`（提交 `a412146401426c0cdff8bbefb8627a03da519da8`）固定为隔离运行时基线。
- AstrBot 位于被 Git 忽略的 `runtime/AstrBot/`；没有修改其核心。
- 已建立 Python 3.12.14 + `uv` 工程环境、领域消息模型、Bangumi 候选筛选器和 Emoji 游戏状态机。
- 已建立 30 道固定题包；所有条目均已对照本地 Bangumi 快照验证为非 NSFW 动画。
- 阶段 1 已完成：领域结果与中文表达分离，并建立单元测试和群聊行为回归样例。
- 已完成 AstrBot 最小启动、插件真实加载与正常关停验证；运行数据仅存在于被忽略的隔离目录。
- 尚未尝试连接 NapCat、QQ、Bangumi API 或 AI 服务。
- 已下载并校验 Bangumi Archive 的 `2026-09-08` 快照到本地 `data/`；尚未解压、导入或接入运行逻辑。
- 阶段 2 已完成：领域包可构建，薄插件可由真实 AstrBot 加载，假事件集成测试通过；尚未连接 QQ。
- 阶段 3 已开始：无凭据部署模板和 fail-closed 群白名单已完成；真实 QQ 联调等待测试标识。

## 当前方向

```text
QQ + NapCatQQ
      ↓ OneBot V11
AstrBot 运行内核
      ↓ 薄适配层
Apeiria Core + Anime Party
      ↓
SQLite / Bangumi / AI
```

Apeiria 是完整产品，AstrBot 是可替换的运行内核。产品核心不能被绑定到 AstrBot 的内部实现。

## 阅读顺序

1. 理解用户体验：`01-PRODUCT.md`
2. 准备结构设计：`02-ARCHITECTURE.md`
3. 准备实施工作：`03-ROADMAP.md`
4. 引入或修改外部项目：`04-UPSTREAM.md`
5. 查询当前结论与未决问题：`05-DECISIONS.md`
6. 新窗口接续当前进度：`06-NEXT-SESSION.md`

只读取当前任务真正需要的部分。
