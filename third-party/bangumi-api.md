# Bangumi API 来源记录

- 官方文档仓库：<https://github.com/bangumi/api>
- OpenAPI 规范：`open-api/v0.yaml`（自 bangumi/server 仓库同步）
- 使用端点：`GET /v0/subjects/{subject_id}`（免鉴权，服务端缓存 300 秒）
- 默认 Base URL：`https://api.bgm.tv`（2026-09-11 真实验证可用）
- User-Agent 约定：`aryuu-git/Apeiria/0.1 (https://github.com/aryuu-git/Apeiria)`（官方要求非浏览器客户端携带开发者 ID 与应用名，开源项目附主页）
- 接入代码：`packages/anime-party/src/anime_party/bangumi_api.py`
- 验证脚本：`packages/anime-party/scripts/verify_bangumi_api.py`

## 当前状态

2026-09-11 真实验证：本机网络直连 `api.bangumi.tv` 与 `api.bgm.tv` 均超时；经系统代理后 `api.bgm.tv` 返回 200 与真实 Subject JSON，`api.bangumi.tv` 仍握手失败。默认域名因此取 `api.bgm.tv`；传输层默认复用系统代理配置。客户端带 SQLite KV 缓存（TTL 7 天、请求间隔 1 秒），API 不可达时安静回退到过期缓存或 `None`，不向调用方抛错。

## 安全边界

- 仅读取公开条目数据，不登录、不携带 Token 或 Cookie。
- 请求间隔不小于 1 秒，遵守官方速率礼仪。
- 缓存只存公开条目 JSON，不存聊天正文。
