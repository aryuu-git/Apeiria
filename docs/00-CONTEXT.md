# 00 项目上下文

## 一句话目标

为约 6 人的熟人动画爱好者 QQ 群构建一个长期存在、有分寸的艾佩理雅陪伴机器人，并以 Emoji 猜动画作为首个游戏闭环。

## 当前状态

- 已建立项目目录和文档骨架。
- 已建立项目级 `AGENTS.md`，其中包含渐进阅读、工程边界和修改约束。
- 已初始化本地 Git，初始分支为 `main`，远程为 `https://github.com/aryuu-git/Apeiria`。
- 已完成 AstrBot 第一轮静态上游评估；`v4.28.0` 是待隔离验证的候选基线。
- 尚未拉取 AstrBot 或其他机器人框架。
- 尚未创建 Python 包、配置文件、数据库和运行环境。
- 尚未尝试连接 NapCat、QQ、Bangumi 或 AI 服务。
- 当前目录不是已确认的可运行实现；不要把空目录误认为已完成模块。

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
