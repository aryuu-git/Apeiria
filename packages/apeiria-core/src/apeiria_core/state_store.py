"""Small persistent state abstraction and SQLite implementation."""

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Protocol


class StateStore(Protocol):
    """Minimal namespaced key-value state required by domain services."""

    def get(self, namespace: str, key: str) -> str | None:
        """Return a stored value or ``None``."""

    def set(self, namespace: str, key: str, value: str) -> None:
        """Atomically store a value."""

    def delete(self, namespace: str, key: str) -> None:
        """Delete a value if present."""


class SQLiteStateStore:
    """SQLite-backed state store with explicit schema migrations."""

    SCHEMA_VERSION = 1

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
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
