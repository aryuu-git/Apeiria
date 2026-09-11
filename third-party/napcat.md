# NapCatQQ 来源记录

- 官方仓库：<https://github.com/NapNeko/NapCatQQ>
- 候选固定版本：`v4.18.19`
- 官方发布时间：2026-08-14
- Windows 发行资产：`NapCat.Shell.Windows.OneKey.zip`
- 下载字节数：`1035630`
- SHA-256：`FA365537039E9EC29730166F3F624EB147074BE18BE64D1981A03F35ECB2A2AF`
- 本地位置：`runtime/NapCat-downloads/` 和 `runtime/NapCat-v4.18.19/`（均被 Git 忽略）
- 下载日期：2026-09-11

## 当前状态

发行资产已从 GitHub 官方 Release 下载、计算哈希并解压，尚未执行安装器或登录 QQ。`NapCatInstaller.exe` 没有 Windows Authenticode 签名；运行前需要 Owner 明确确认并在可见界面完成登录或安全验证。

## 安全边界

- 仅使用专用测试 QQ。
- WebUI 与 OneBot 反向 WebSocket 只绑定本机回环地址。
- Token、Cookie、登录二维码和真实聊天正文不得提交。
- 安装完成并通过真实链路验收后，才把该候选版本标记为已验证固定版本。
