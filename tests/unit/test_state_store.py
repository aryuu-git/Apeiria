import sqlite3
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
        assert connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone() == (1,)


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
