# Bangumi Archive 数据来源

## 用途

为 Apeiria 的动画条目筛选、别名整理和题包生成提供离线候选数据。原始归档属于可重新获取的运行数据，不提交到 Git。

## 当前快照

| 项目 | 值 |
| --- | --- |
| 上游 | `bangumi/Archive` |
| 上游仓库 | <https://github.com/bangumi/Archive> |
| 官方最新文件元数据 | <https://raw.githubusercontent.com/bangumi/Archive/master/aux/latest.json> |
| 文件名 | `dump-2026-09-08.210336Z.zip` |
| 上游生成时间 | `2026-09-08T21:03:37Z` |
| 文件大小 | `437079490` 字节 |
| SHA-256 | `df03159ba0e1767c6a6b0d6dec2a2ef47a821d52ecfd0b66bbf8d36126724c3f` |
| 本地位置 | `data/bangumi/archive/dump-2026-09-08.210336Z.zip` |
| 下载与校验日期 | `2026-09-11` |

## 内容

归档包含 9 个 JSON Lines 文件：条目、人物、角色、章节，以及它们之间的关联数据。Apeiria 第一阶段只需要流式读取 `subject.jsonlines`，并筛选 `type == 2` 的动画条目；暂不全量解压或导入数据库。

## 使用边界

- 上游说明此归档是定期导出的 Bangumi Wiki 公共数据，用于减少实时爬取。
- 上游仓库当前未提供单独的 `LICENSE` 文件；在公开分发原始数据、衍生题库或商业使用前，需要进一步确认数据授权与署名要求。
- 当前仅供项目开发期间本地使用，不重新分发归档文件。
- 生成题包时默认排除 `nsfw == true` 条目，并避免直接复制长篇简介或其他可能受版权保护的文本。

