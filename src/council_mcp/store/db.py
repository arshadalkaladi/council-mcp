"""SQLite connection factory + migration runner (standard library only)."""

from __future__ import annotations

import sqlite3

from .migrations import MIGRATIONS


def connect(path: str) -> sqlite3.Connection:
    """Open a connection with WAL, foreign keys, and a busy timeout."""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    # WAL: durable + better concurrency; no-op harmless on :memory:.
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def migrate(conn: sqlite3.Connection) -> int:
    """Apply pending migrations. Returns the resulting schema version.

    Version is tracked in PRAGMA user_version, so re-running is idempotent.
    """
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    for index, sql in enumerate(MIGRATIONS, start=1):
        if index > version:
            conn.executescript(sql)
            conn.execute(f"PRAGMA user_version = {index}")
            version = index
    conn.commit()
    return version


def journal_mode(conn: sqlite3.Connection) -> str:
    return conn.execute("PRAGMA journal_mode").fetchone()[0]
