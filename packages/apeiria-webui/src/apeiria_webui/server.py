"""Loopback management WebUI: live event stream, status, config snapshot.

Read-only by design: the UI observes the same SQLite database the plugin
writes and mirrors the plugin configuration with secrets masked. Editing
stays in the AstrBot Dashboard, which owns plugin configuration lifecycle
and hot reload. Bind to 127.0.0.1 only.
"""

import json
import sqlite3
import time
from contextlib import closing
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from apeiria_webui.page import render_page

_SENSITIVE_KEYS = ("api_key", "token", "secret", "password", "cookie")


@dataclass(frozen=True, slots=True)
class WebUIContext:
    """Runtime locations the WebUI reads from."""

    db_path: Path
    config_path: Path | None
    dashboard_url: str = "http://127.0.0.1:6185"


def _connect_readonly(db_path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True, timeout=5)


def _mask(value: str) -> str:
    return value[:4] + "****" if len(value) > 8 else "****"


def _masked_config(config_path: Path | None) -> dict[str, Any]:
    if config_path is None or not config_path.exists():
        return {}
    try:
        config = json.loads(config_path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(config, dict):
        return {}
    return {
        key: (_mask(str(value)) if any(s in key.lower() for s in _SENSITIVE_KEYS) else value)
        for key, value in config.items()
    }


def _fetch_events(db_path: Path, last_id: int, limit: int = 200) -> list[dict[str, Any]]:
    """Return events newer than ``last_id``; tolerate pre-v2 databases."""
    try:
        with closing(_connect_readonly(db_path)) as connection:
            rows = connection.execute(
                "SELECT id, ts, kind, session_id, payload FROM events "
                "WHERE id > ? ORDER BY id LIMIT ?",
                (last_id, limit),
            ).fetchall()
    except sqlite3.OperationalError:
        return []
    events: list[dict[str, Any]] = []
    for row in rows:
        try:
            payload = json.loads(str(row[4]))
        except json.JSONDecodeError:
            payload = {"raw": str(row[4])}
        events.append(
            {
                "id": int(row[0]),
                "ts": float(row[1]),
                "kind": str(row[2]),
                "session_id": str(row[3]),
                "payload": payload,
            }
        )
    return events


def _fetch_status(db_path: Path, config: dict[str, Any]) -> dict[str, Any]:
    """Report game state per group and autonomous-speech budget usage.

    Every query degrades independently: a pre-v2 database reports
    ``events_ready: false`` but still exposes game state and rate budget.
    """
    status: dict[str, Any] = {"groups": [], "rates": [], "events_ready": False}
    try:
        with closing(_connect_readonly(db_path)) as connection:
            try:
                connection.execute("SELECT COUNT(*) FROM events").fetchone()
                status["events_ready"] = True
            except sqlite3.OperationalError:
                status["events_ready"] = False
            game_rows = connection.execute(
                "SELECT key, value FROM state WHERE namespace = 'anime-party'"
            ).fetchall()
            for key, value in game_rows:
                try:
                    game = json.loads(str(value))
                except json.JSONDecodeError:
                    game = {"raw": str(value)}
                status["groups"].append({"session": str(key), "game": game})
            rate_rows = connection.execute(
                "SELECT key, value FROM state WHERE namespace = 'companion' "
                "AND key LIKE 'rate-%'"
            ).fetchall()
    except sqlite3.OperationalError:
        return status
    window_seconds = float(config.get("ai_rate_window_minutes", 10)) * 60.0
    limit = int(config.get("ai_autonomous_rate_limit", 5))
    now = time.time()
    for key, value in rate_rows:
        try:
            stamps = [float(stamp) for stamp in json.loads(str(value))]
        except (json.JSONDecodeError, TypeError, ValueError):
            stamps = []
        used = sum(1 for stamp in stamps if now - stamp < window_seconds)
        status["rates"].append(
            {
                "session": str(key).removeprefix("rate-"),
                "used": used,
                "limit": limit,
                "window_seconds": window_seconds,
            }
        )
    return status


class ApeiriaWebUIHandler(BaseHTTPRequestHandler):
    """Serve the page and its JSON API from one thread per request."""

    server: "ApeiriaWebUIServer"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        ctx = self.server.context
        if parsed.path == "/":
            html = render_page(ctx.dashboard_url).encode("utf-8")
            self._send(200, "text/html; charset=utf-8", html)
            return
        if parsed.path == "/api/events":
            query = parse_qs(parsed.query)
            try:
                since = int(query.get("since", ["0"])[0])
            except ValueError:
                since = 0
            events = _fetch_events(ctx.db_path, since)
            last_id = since
            for event in events:
                last_id = max(last_id, int(event["id"]))
            self._send_json(200, {"events": events, "last_id": last_id})
            return
        if parsed.path == "/api/status":
            self._send_json(200, _fetch_status(ctx.db_path, _masked_config(ctx.config_path)))
            return
        if parsed.path == "/api/config":
            self._send_json(200, {"config": _masked_config(ctx.config_path)})
            return
        self._send(404, "text/plain; charset=utf-8", b"not found")

    def _send(self, status: int, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send(status, "application/json; charset=utf-8", body)

    def log_message(self, format: str, *args: Any) -> None:
        pass


class ApeiriaWebUIServer(ThreadingHTTPServer):
    """Threaded loopback server carrying the WebUI context."""

    daemon_threads = True

    def __init__(self, context: WebUIContext, host: str, port: int) -> None:
        self.context = context
        super().__init__((host, port), ApeiriaWebUIHandler)
