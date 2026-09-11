import json
import sqlite3
import time
from pathlib import Path

import pytest

from apeiria_core import SQLiteStateStore


def test_sqlite_state_store_migrates_and_persists(tmp_path: Path) -> None:
    database = tmp_path / "state.db"
    first = SQLiteStateStore(database)

    first.set("games", "group:1", '{"status":"active"}')
    reopened = SQLiteStateStore(database)

    assert reopened.get("games", "group:1") == '{"status":"active"}'
    reopened.delete("games", "group:1")
    assert reopened.get("games", "group:1") is None
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone() == (2,)


def test_sqlite_state_store_rejects_newer_schema(tmp_path: Path) -> None:
    database = tmp_path / "future.db"
    with sqlite3.connect(database) as connection:
        connection.execute(
            "CREATE TABLE schema_migrations "
            "(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
        )
        connection.execute(
            "INSERT INTO schema_migrations(version, applied_at) VALUES (99, CURRENT_TIMESTAMP)"
        )

    with pytest.raises(RuntimeError, match="newer"):
        SQLiteStateStore(database)


def test_sqlite_state_store_upgrades_v1_database_to_v2(tmp_path: Path) -> None:
    database = tmp_path / "state.db"
    with sqlite3.connect(database) as connection:
        connection.execute(
            "CREATE TABLE schema_migrations "
            "(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
        )
        connection.execute(
            "CREATE TABLE state ("
            "namespace TEXT NOT NULL, key TEXT NOT NULL, value TEXT NOT NULL, "
            "updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, "
            "PRIMARY KEY (namespace, key))"
        )
        connection.execute("INSERT INTO schema_migrations(version) VALUES (1)")
        connection.execute(
            "INSERT INTO state(namespace, key, value) VALUES ('games', 'g1', '{}')"
        )

    store = SQLiteStateStore(database)

    assert store.get("games", "g1") == "{}"
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0] == 2
        assert connection.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0


def test_event_log_append_read_and_prune(tmp_path: Path) -> None:
    store = SQLiteStateStore(tmp_path / "state.db", event_retention_seconds=10.0)

    first = store.append_event("companion.decision", "s1", {"speak": True, "text": "在"})
    second = store.append_event("game.reply", "s1", {"text": "猜猜这部动画："})

    assert first == 1
    assert second == 2
    events = store.events_since(0)
    assert [event["kind"] for event in events] == ["companion.decision", "game.reply"]
    assert events[1]["payload"]["text"].startswith("猜猜")
    assert store.events_since(first) == [events[1]]

    with sqlite3.connect(tmp_path / "state.db") as connection:
        connection.execute("UPDATE events SET ts = ?", (time.time() - 100.0,))

    store.prune_events()
    assert store.events_since(0) == []
    assert json.dumps(events[0]["payload"], ensure_ascii=False)
