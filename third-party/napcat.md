# NapCatQQ 来源记录

- 官方仓库：<https://github.com/NapNeko/NapCatQQ>
- 固定版本：`v4.18.19`
- 官方发布时间：2026-08-14
- Windows 发行资产：`NapCat.Shell.Windows.OneKey.zip`
- 下载字节数：`1035630`
- SHA-256：`FA365537039E9EC29730166F3F624EB147074BE18BE64D1981A03F35ECB2A2AF`
- 本地位置：`runtime/NapCat-downloads/` 和 `runtime/NapCat-v4.18.19/`（均被 Git 忽略）
- 下载日期：2026-09-11
- 实际运行资产：`NapCat.Shell.zip`
- 实际运行资产 SHA-256：`C5B7423D1D5B8C555D62CD9E4059B1908CC0986E7B5C85A0F450F4A8ED170ACF`

## 当前状态

官方轻量一键安装器因其 QQ 下载地址返回 404 而失败，该问题与上游公开问题报告一致。随后改用同一 Release 的官方 `NapCat.Shell.zip` 和机器上已有的 QQ，通过 Owner 扫码完成专用测试账号登录。NapCat 与 AstrBot 的 OneBot V11 反向 WebSocket、真实目标群收发和静默控制已验证。

## 安全边界

- 仅使用专用测试 QQ。
- WebUI 与 OneBot 反向 WebSocket 只绑定本机回环地址。
- Token、Cookie、登录二维码和真实聊天正文不得提交。
- 安装完成并通过真实链路验收后，才把该候选版本标记为已验证固定版本。
