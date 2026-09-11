# NapCat / OneBot V11 本机联调

本目录只保存可公开的说明和示例，不保存 QQ 凭据、Token、Cookie、二维码或真实群号。

## 固定拓扑

```text
NapCat（反向 WebSocket 客户端）
  -> ws://127.0.0.1:6199/ws
AstrBot OneBot v11（服务端）
  -> astrbot-plugin-apeiria
```

AstrBot Dashboard 保持绑定 `127.0.0.1:6185`。OneBot 服务也只绑定本机回环地址；不得向公网开放 6185 或 6199。

## 联调前准备

1. 将 `apeiria.local.example.json` 复制为 `apeiria.local.json`。
2. 填入专用测试 QQ、唯一测试群和管理员 QQ；这个本地文件已由 `*.local.json` 忽略。
3. 生成一个随机 OneBot Token，分别填入 AstrBot 和 NapCat 的本地配置，不能提交或写入日志。
4. 在 AstrBot 创建 `OneBot v11` 平台：主机 `127.0.0.1`、端口 `6199`、Token 与 NapCat 相同。
5. 在 Apeiria 插件配置中把 `allowed_group_ids` 设为唯一测试群。空列表会拒绝所有群，属于安全默认值。
6. 在 NapCat 添加反向 WebSocket 客户端：URL `ws://127.0.0.1:6199/ws`，Token 与 AstrBot 相同。

真实连接成功的判据是 AstrBot 日志出现 `aiocqhttp(OneBot v11) 适配器已连接。`。联调期间还需逐项验证收发、重复事件、群外拒绝、静默和重载。

## 安全边界

- 只使用专用测试 QQ，不使用 Owner 的主账号。
- 初次测试只允许一个小群；插件采用 fail-closed 白名单。
- 不截取或提交真实聊天正文。
- NapCat 版本及来源必须在安装时写入 `third-party/napcat.md`。
- 安装、升级和登录前先核对 NapCat 官方发布信息与当前 QQ 风控提示。
