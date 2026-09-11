# 02 架构与目录

## 分层结构

```text
NapCat / OneBot V11
        ↓
AstrBot runtime
        ↓
astrbot-plugin-apeiria
        ↓
apeiria-core ─── anime-party
        ↓              ↓
   会话与人格     SQLite / Bangumi / AI
```

## 依赖方向

- 适配层可以依赖 Apeiria 核心；核心不能反向依赖 AstrBot。
- 游戏可以通过核心定义的接口收发事件，但不能直接操作 QQ 事件对象。
- 外部服务通过接口注入，允许使用假实现进行离线测试。
- 持久化只保存必要状态，不让数据库模型渗透到全部业务层。

## 一级目录

| 目录 | 用途 |
| --- | --- |
| `runtime` | AstrBot 固定版本或受控 fork |
| `packages` | 自研核心、游戏与适配器 |
| `persona` | 人格配置和行为样例 |
| `deploy` | Windows 与 NapCat 部署材料 |
| `tests` | 单元、集成、对话回归测试 |
| `data` | 本地运行数据和可重建缓存 |
| `third-party` | 上游来源、版本和许可证 |

## 关键非功能要求

- 确定性状态机与消息幂等。
- 超时、限流、有限重试和故障降级。
- 密钥与日志脱敏。
- 数据库迁移、备份和恢复验证。
- 上游升级可测试、可回滚。
