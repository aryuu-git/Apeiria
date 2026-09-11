"""Single-page HTML for the Apeiria management WebUI."""

DASHBOARD_LINK = '<a href="{url}" target="_blank">AstrBot Dashboard</a>'

_PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>Apeiria 管理台</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body { margin: 0; font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
         background: #12141a; color: #d7dae0; }
  header { padding: 14px 20px; background: #191c24; border-bottom: 1px solid #2a2e3a;
           display: flex; align-items: baseline; gap: 16px; }
  header h1 { margin: 0; font-size: 18px; color: #9fb8ff; }
  header a { color: #7fb0ff; font-size: 13px; }
  main { display: grid; grid-template-columns: 320px 1fr; gap: 14px; padding: 14px 20px; }
  .card { background: #191c24; border: 1px solid #2a2e3a; border-radius: 10px;
          padding: 12px 14px; }
  .card h2 { margin: 0 0 8px; font-size: 14px; color: #8fd0a8; }
  .card h2.blue { color: #8fb8ff; }
  .kv { font-size: 13px; line-height: 1.7; }
  .kv b { color: #e8eaf0; }
  .muted { color: #7a8090; font-size: 12px; }
  #events { height: calc(100vh - 150px); overflow-y: auto; }
  .event { border-bottom: 1px solid #23273350; padding: 6px 4px; font-size: 13px; }
  .event .meta { color: #7a8090; font-size: 11px; }
  .badge { display: inline-block; padding: 1px 7px; border-radius: 8px;
           font-size: 11px; margin-right: 6px; background: #2a2e3a; color: #cfd4e0; }
  .badge.companion.decision { background: #1d3a2a; color: #8fe0a8; }
  .badge.companion.gate { background: #16324a; color: #8fc0ff; }
  .badge.companion.action { background: #3a2a1d; color: #ffc08f; }
  .badge.game.reply { background: #331d3a; color: #d98fff; }
  .badge.message.skip { background: #333340; color: #9095a5; }
  pre { margin: 4px 0 0; font-size: 12px; white-space: pre-wrap; word-break: break-all;
        color: #aab0c0; }
  .err { color: #ff9f9f; }
</style>
</head>
<body>
<header>
  <h1>艾佩理雅 · 管理台</h1>
  <span class="muted">只读观测 · 配置编辑请前往 DASHBOARD</span>
</header>
<main>
  <div>
    <div class="card">
      <h2>运行状态</h2>
      <div id="status" class="kv muted">加载中…</div>
    </div>
    <div class="card" style="margin-top:14px">
      <h2 class="blue">插件配置（密钥已掩码）</h2>
      <div id="config" class="kv muted">加载中…</div>
    </div>
  </div>
  <div class="card">
    <h2>实时事件流 <span class="muted" id="cursor"></span></h2>
    <div id="events"><div class="muted">等待事件…</div></div>
  </div>
</main>
<script>
const KIND_LABELS = {
  "companion.gate": "门控", "companion.decision": "决策",
  "companion.action": "动作", "game.reply": "游戏", "control.reply": "控制",
  "message.skip": "跳过",
};
const since = { value: 0 };

function esc(s) { return String(s).replace(/[&<>"]/g, c => (
  {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c])); }

function fmtTime(ts) {
  return new Date(ts * 1000).toLocaleTimeString("zh-CN", { hour12: false });
}

function renderEvent(ev) {
  const badge = KIND_LABELS[ev.kind] ? ev.kind : ev.kind;
  const div = document.createElement("div");
  div.className = "event";
  div.innerHTML =
    `<span class="badge ${esc(ev.kind)}">${esc(KIND_LABELS[ev.kind] || ev.kind)}</span>` +
    `<span class="meta">${fmtTime(ev.ts)} · ${esc(ev.session_id)}</span>` +
    `<pre>${esc(JSON.stringify(ev.payload, null, 2))}</pre>`;
  return div;
}

async function pollEvents() {
  try {
    const res = await fetch(`/api/events?since=${since.value}`);
    const data = await res.json();
    const box = document.getElementById("events");
    for (const ev of data.events) box.prepend(renderEvent(ev));
    if (data.events.length) {
      since.value = data.last_id;
      document.getElementById("cursor").textContent = `#${data.last_id}`;
    }
  } catch (e) { /* 服务未就绪时静默重试 */ }
}

async function refreshStatus() {
  try {
    const res = await fetch("/api/status");
    const s = await res.json();
    const el = document.getElementById("status");
    if (!s.events_ready) { el.innerHTML = "事件库尚未就绪（等待插件部署 schema v2）。"; return; }
    const groups = s.groups.map(g =>
      `<div>群 <b>${esc(g.session)}</b> 状态 ` +
      `<b>${esc(JSON.stringify(g.game.status ?? g.game))}</b></div>`
    ).join("") || "<div class='muted'>暂无游戏状态</div>";
    const rates = s.rates.map(r =>
      `<div>${esc(r.session)}：${r.used}/${r.limit} 次 / ` +
      `${Math.round(r.window_seconds / 60)} 分钟</div>`
    ).join("") || "<div class='muted'>无限频记录</div>";
    el.innerHTML = groups + "<hr style='border-color:#2a2e3a'>" + rates;
  } catch (e) { /* ignore */ }
}

async function loadConfig() {
  try {
    const res = await fetch("/api/config");
    const data = await res.json();
    const rows = Object.entries(data.config).map(([k, v]) =>
      `<div>${esc(k)}：<b>${esc(typeof v === "object" ? JSON.stringify(v) : v)}</b></div>`);
    document.getElementById("config").innerHTML = rows.join("") || "未找到配置文件";
  } catch (e) { /* ignore */ }
}

refreshStatus(); loadConfig();
setInterval(pollEvents, 1200);
setInterval(refreshStatus, 5000);
pollEvents();
</script>
</body>
</html>
"""


def render_page(dashboard_url: str) -> str:
    """Return the management page with the Dashboard link filled in."""
    link = f'<a href="{dashboard_url}" target="_blank">AstrBot Dashboard</a>'
    return _PAGE.replace("DASHBOARD", link)
