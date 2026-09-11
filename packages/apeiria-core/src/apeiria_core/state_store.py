"""Small persistent state abstraction, SQLite implementation, event log."""

import json
import sqlite3
import time
from contextlib import closing
from pathlib import Path
from typing import Any, Protocol

DEFAULT_EVENT_RETENTION_SECONDS = 7 * 24 * 3600.0
_EVENT_PRUNE_INTERVAL = 256


class StateStore(Protocol):
    """Minimal namespaced key-value state required by domain services."""

    def get(self, namespace: str, key: str) -> str | None:
        """Return a stored value or ``None``."""

    def set(self, namespace: str, key: str, value: str) -> None:
        """Atomically store a value."""

    def delete(self, namespace: str, key: str) -> None:
        """Delete a value if present."""


class EventSink(Protocol):
    """Minimal observability sink required by the plugin adapter."""

    def append_event(self, kind: str, session_id: str, payload: dict[str, Any]) -> int:
        """Store one event and return its id."""


class SQLiteStateStore:
    """SQLite-backed state store and event log with explicit migrations.

    Schema history: v1 adds the ``state`` key-value table; v2 adds the
    append-only ``events`` table used for the management WebUI and logs.
    Events carry the message text needed for local observability, live in
    the git-ignored runtime database only, and are pruned after
    ``event_retention_seconds``.
    """

    SCHEMA_VERSION = 2

    def __init__(
        self,
        path: Path,
        *,
        event_retention_seconds: float = DEFAULT_EVENT_RETENTION_SECONDS,
    ) -> None:
        self.path = path
        self.event_retention_seconds = event_retention_seconds
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._appended_events = 0
        self._migrate()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=5)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def _migrate(self) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations "
                "(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
            )
            current = connection.execute(
                "SELECT COALESCE(MAX(version), 0) FROM schema_migrations"
            ).fetchone()[0]
            if current > self.SCHEMA_VERSION:
                raise RuntimeError("state database schema is newer than this application")
            if current < 1:
                connection.execute(
                    "CREATE TABLE state ("
                    "namespace TEXT NOT NULL, key TEXT NOT NULL, value TEXT NOT NULL, "
                    "updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, "
                    "PRIMARY KEY (namespace, key))"
                )
                connection.execute("INSERT INTO schema_migrations(version) VALUES (1)")
            if current < 2:
                connection.execute(
                    "CREATE TABLE events ("
                    "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                    "ts REAL NOT NULL, kind TEXT NOT NULL, "
                    "session_id TEXT NOT NULL, payload TEXT NOT NULL)"
                )
                connection.execute("INSERT INTO schema_migrations(version) VALUES (2)")
        self.prune_events()

    # -- key-value state -------------------------------------------------

    def get(self, namespace: str, key: str) -> str | None:
        with closing(self._connect()) as connection, connection:
            row = connection.execute(
                "SELECT value FROM state WHERE namespace = ? AND key = ?",
                (namespace, key),
            ).fetchone()
        return None if row is None else str(row[0])

    def set(self, namespace: str, key: str, value: str) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute(
                "INSERT INTO state(namespace, key, value) VALUES (?, ?, ?) "
                "ON CONFLICT(namespace, key) DO UPDATE SET "
                "value = excluded.value, updated_at = CURRENT_TIMESTAMP",
                (namespace, key, value),
            )

    def delete(self, namespace: str, key: str) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute(
                "DELETE FROM state WHERE namespace = ? AND key = ?",
                (namespace, key),
            )

    # -- event log --------------------------------------------------------

    def append_event(self, kind: str, session_id: str, payload: dict[str, Any]) -> int:
        """Append one observability event and return its id."""
        with closing(self._connect()) as connection, connection:
            cursor = connection.execute(
                "INSERT INTO events(ts, kind, session_id, payload) VALUES (?, ?, ?, ?)",
                (time.time(), kind, session_id, json.dumps(payload, ensure_ascii=False)),
            )
            event_id = int(cursor.lastrowid or 0)
        self._appended_events += 1
        if self._appended_events % _EVENT_PRUNE_INTERVAL == 0:
            self.prune_events()
        return event_id

    def events_since(self, last_id: int = 0, limit: int = 200) -> list[dict[str, Any]]:
        """Return events newer than ``last_id`` in ascending order."""
        with closing(self._connect()) as connection, connection:
            rows = connection.execute(
                "SELECT id, ts, kind, session_id, payload FROM events "
                "WHERE id > ? ORDER BY id LIMIT ?",
                (last_id, limit),
            ).fetchall()
        return [
            {
                "id": int(row[0]),
                "ts": float(row[1]),
                "kind": str(row[2]),
                "session_id": str(row[3]),
                "payload": json.loads(str(row[4])),
            }
            for row in rows
        ]

    def prune_events(self) -> None:
        """Delete events older than the retention window."""
        floor = time.time() - self.event_retention_seconds
        with closing(self._connect()) as connection, connection:
            connection.execute("DELETE FROM events WHERE ts < ?", (floor,))
