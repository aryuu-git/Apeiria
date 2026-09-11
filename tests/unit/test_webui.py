"""Unit tests for the loopback management WebUI."""

import json
import sqlite3
import threading
import time
import urllib.request
from pathlib import Path

import pytest

from apeiria_core import SQLiteStateStore
from apeiria_webui import ApeiriaWebUIServer, WebUIContext


@pytest.fixture()
def runtime(tmp_path: Path) -> tuple[Path, Path]:
    store = SQLiteStateStore(tmp_path / "state.db")
    store.append_event("companion.decision", "s1", {"speak": True, "text": "在"})
    store.append_event("game.reply", "s1", {"kind": "question", "messages": ["猜"]})
    store.set("anime-party", "apeiria-onebot:GroupMessage:690947065", '{"status":"idle"}')
    store.set("companion", "rate-apeiria-onebot:GroupMessage:690947065", json.dumps([time.time()]))
    config = tmp_path / "config.json"
    config.write_text(
        json.dumps(
            {
                "ai_enabled": True,
                "ai_api_key": "ark-12345678-abcdef-987654",
                "ai_autonomous_rate_limit": 5,
                "ai_rate_window_minutes": 10,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return tmp_path / "state.db", config


@pytest.fixture()
def server(runtime: tuple[Path, Path]):
    db_path, config_path = runtime
    context = WebUIContext(db_path=db_path, config_path=config_path)
    server = ApeiriaWebUIServer(context, "127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def test_events_api_streams_since_cursor(server: str) -> None:
    first = _get_json(f"{server}/api/events?since=0")
    assert [event["kind"] for event in first["events"]] == [
        "companion.decision",
        "game.reply",
    ]
    assert first["last_id"] == 2

    second = _get_json(f"{server}/api/events?since={first['last_id']}")
    assert second["events"] == []
    assert second["last_id"] == 2


def test_status_api_reports_game_and_rate(server: str) -> None:
    status = _get_json(f"{server}/api/status")

    assert status["events_ready"] is True
    assert status["groups"][0]["session"] == "apeiria-onebot:GroupMessage:690947065"
    assert status["groups"][0]["game"] == {"status": "idle"}
    assert status["rates"][0]["used"] == 1
    assert status["rates"][0]["limit"] == 5


def test_config_api_masks_secrets(server: str) -> None:
    data = _get_json(f"{server}/api/config")

    assert data["config"]["ai_enabled"] is True
    assert data["config"]["ai_api_key"] == "ark-****"
    assert "987654" not in json.dumps(data)


def test_page_served_with_dashboard_link(server: str) -> None:
    with urllib.request.urlopen(f"{server}/", timeout=5) as response:
        html = response.read().decode("utf-8")
    assert "艾佩理雅 · 管理台" in html
    assert "http://127.0.0.1:6185" in html


def test_events_api_tolerates_pre_v2_database(tmp_path: Path) -> None:
    old_db = tmp_path / "old.db"
    with sqlite3.connect(old_db) as connection:
        connection.execute(
            "CREATE TABLE state (namespace TEXT NOT NULL, key TEXT NOT NULL, "
            "value TEXT NOT NULL, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, "
            "PRIMARY KEY (namespace, key))"
        )
    context = WebUIContext(db_path=old_db, config_path=None)
    server = ApeiriaWebUIServer(context, "127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_address[1]}"
        data = _get_json(f"{base}/api/events?since=0")
        assert data == {"events": [], "last_id": 0}
        status = _get_json(f"{base}/api/status")
        assert status == {"groups": [], "rates": [], "events_ready": False}
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
