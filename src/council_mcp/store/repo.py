"""Store: account-scoped operations over the SQLite schema.

Every method takes account_id and filters on it. There is intentionally no
"get by id without account" method — the account scope is not optional. This is
the single enforcement point for cross-account isolation.

Council state-machine semantics live in Phase 2A; job claim/retry/recovery live
in Phase 1E. This module provides the durable, atomic, account-scoped mechanism
those phases build on.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from . import db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row(cursor_row: sqlite3.Row | None) -> dict | None:
    return dict(cursor_row) if cursor_row is not None else None


class DuplicateError(Exception):
    """Raised when creating a record whose primary key already exists."""


class Store:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def close(self) -> None:
        self._conn.close()

    # -- deliberations ---------------------------------------------------
    def create_deliberation(self, account_id: str, deliberation_id: str,
                            question: str, status: str = "QUEUED",
                            *, now: str | None = None) -> dict:
        ts = now or _now()
        try:
            with self._conn:
                self._conn.execute(
                    "INSERT INTO deliberations "
                    "(deliberation_id, account_id, question, status, partial, "
                    " created_at, updated_at) VALUES (?, ?, ?, ?, 0, ?, ?)",
                    (deliberation_id, account_id, question, status, ts, ts),
                )
        except sqlite3.IntegrityError as exc:
            raise DuplicateError(f"deliberation exists: {deliberation_id}") from exc
        return self.get_deliberation(account_id, deliberation_id)

    def get_deliberation(self, account_id: str, deliberation_id: str) -> dict | None:
        cur = self._conn.execute(
            "SELECT * FROM deliberations WHERE deliberation_id = ? AND account_id = ?",
            (deliberation_id, account_id),
        )
        return _row(cur.fetchone())

    def list_deliberations(self, account_id: str) -> list[dict]:
        cur = self._conn.execute(
            "SELECT * FROM deliberations WHERE account_id = ? ORDER BY created_at",
            (account_id,),
        )
        return [dict(r) for r in cur.fetchall()]

    def update_deliberation_status(self, account_id: str, deliberation_id: str,
                                   new_status: str, *, expected_status: str | None = None,
                                   partial: bool | None = None, terminal: bool = False,
                                   now: str | None = None) -> bool:
        """Atomic status update, scoped to account. Returns True iff one row changed.

        If expected_status is given, the update only applies when the current
        status matches (optimistic concurrency guard).
        """
        ts = now or _now()
        sets = ["status = ?", "updated_at = ?"]
        params: list = [new_status, ts]
        if partial is not None:
            sets.append("partial = ?")
            params.append(1 if partial else 0)
        if terminal:
            sets.append("terminal_at = ?")
            params.append(ts)
        where = "deliberation_id = ? AND account_id = ?"
        tail: list = [deliberation_id, account_id]
        if expected_status is not None:
            where += " AND status = ?"
            tail.append(expected_status)
        sql = f"UPDATE deliberations SET {', '.join(sets)} WHERE {where}"
        with self._conn:
            cur = self._conn.execute(sql, params + tail)
        return cur.rowcount == 1

    # -- audit -----------------------------------------------------------
    def append_audit(self, account_id: str, deliberation_id: str, type_: str,
                     detail: str | None = None, *, now: str | None = None) -> int | None:
        """Append an audit event, but only if the deliberation is owned by
        account_id. Returns the event_id, or None if not owned."""
        ts = now or _now()
        with self._conn:
            cur = self._conn.execute(
                "INSERT INTO audit_events (deliberation_id, account_id, ts, type, detail) "
                "SELECT ?, ?, ?, ?, ? WHERE EXISTS "
                "(SELECT 1 FROM deliberations WHERE deliberation_id = ? AND account_id = ?)",
                (deliberation_id, account_id, ts, type_, detail, deliberation_id, account_id),
            )
            if cur.rowcount == 1:
                return cur.lastrowid
        return None

    def list_audit(self, account_id: str, deliberation_id: str) -> list[dict]:
        cur = self._conn.execute(
            "SELECT * FROM audit_events WHERE account_id = ? AND deliberation_id = ? "
            "ORDER BY event_id",
            (account_id, deliberation_id),
        )
        return [dict(r) for r in cur.fetchall()]

    # -- jobs (table + minimal ops; claim/retry/recovery arrive in 1E) ---
    def create_job(self, account_id: str, job_id: str, kind: str, ref_id: str,
                   *, state: str = "QUEUED", max_attempts: int = 3,
                   now: str | None = None) -> dict:
        ts = now or _now()
        try:
            with self._conn:
                self._conn.execute(
                    "INSERT INTO jobs (job_id, account_id, kind, ref_id, state, "
                    " attempts, max_attempts, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?)",
                    (job_id, account_id, kind, ref_id, state, max_attempts, ts, ts),
                )
        except sqlite3.IntegrityError as exc:
            raise DuplicateError(f"job exists: {job_id}") from exc
        return self.get_job(account_id, job_id)

    def get_job(self, account_id: str, job_id: str) -> dict | None:
        cur = self._conn.execute(
            "SELECT * FROM jobs WHERE job_id = ? AND account_id = ?",
            (job_id, account_id),
        )
        return _row(cur.fetchone())

    # -- jobs: TRUSTED INFRASTRUCTURE (worker) ---------------------------
    # These are NOT account-scoped: the background worker is server
    # infrastructure and processes every account's jobs. They must NEVER be
    # called from a user-request path. User-facing job reads use get_job()
    # (account-scoped) above. Account isolation of the WORK is preserved
    # because each job carries its account_id, which handlers use to scope
    # their own reads/writes.
    def _get_job_any(self, job_id: str) -> dict | None:
        cur = self._conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
        return _row(cur.fetchone())

    def claim_next_job(self, *, now: str | None = None) -> dict | None:
        """Atomically claim the oldest QUEUED job (QUEUED -> CLAIMED).

        Concurrency-safe: the guarded UPDATE (WHERE state='QUEUED') means only
        one claimer wins; losers get rowcount 0 and see None.
        """
        ts = now or _now()
        with self._conn:
            row = self._conn.execute(
                "SELECT job_id FROM jobs WHERE state = 'QUEUED' "
                "ORDER BY created_at, job_id LIMIT 1"
            ).fetchone()
            if row is None:
                return None
            job_id = row[0]
            cur = self._conn.execute(
                "UPDATE jobs SET state = 'CLAIMED', claimed_at = ?, updated_at = ? "
                "WHERE job_id = ? AND state = 'QUEUED'",
                (ts, ts, job_id),
            )
            if cur.rowcount != 1:
                return None  # lost the race; caller may retry
        return self._get_job_any(job_id)

    def mark_job_running(self, job_id: str, *, now: str | None = None) -> bool:
        ts = now or _now()
        with self._conn:
            cur = self._conn.execute(
                "UPDATE jobs SET state = 'RUNNING', updated_at = ? "
                "WHERE job_id = ? AND state = 'CLAIMED'",
                (ts, job_id),
            )
        return cur.rowcount == 1

    def mark_job_succeeded(self, job_id: str, *, now: str | None = None) -> bool:
        ts = now or _now()
        with self._conn:
            cur = self._conn.execute(
                "UPDATE jobs SET state = 'SUCCEEDED', updated_at = ? "
                "WHERE job_id = ? AND state IN ('CLAIMED', 'RUNNING')",
                (ts, job_id),
            )
        return cur.rowcount == 1

    def mark_job_failed(self, job_id: str, error: str | None = None,
                        *, now: str | None = None) -> str | None:
        """Record a failure: attempts++, then requeue (QUEUED) if attempts
        remain, else DEAD. Returns the new state, or None if not transitionable.
        """
        ts = now or _now()
        with self._conn:
            row = self._conn.execute(
                "SELECT attempts, max_attempts FROM jobs "
                "WHERE job_id = ? AND state IN ('CLAIMED', 'RUNNING')",
                (job_id,),
            ).fetchone()
            if row is None:
                return None
            attempts = row["attempts"] + 1
            new_state = "DEAD" if attempts >= row["max_attempts"] else "QUEUED"
            self._conn.execute(
                "UPDATE jobs SET state = ?, attempts = ?, error = ?, "
                "claimed_at = NULL, updated_at = ? WHERE job_id = ?",
                (new_state, attempts, error, ts, job_id),
            )
        return new_state

    def recover_stale_jobs(self, *, now: str | None = None,
                           stale_before: str | None = None) -> int:
        """Reset in-flight jobs (CLAIMED/RUNNING) back to QUEUED. Called on
        startup after a crash (no worker is actually running them). With
        stale_before set, only jobs claimed before that timestamp are reset."""
        ts = now or _now()
        with self._conn:
            if stale_before is None:
                cur = self._conn.execute(
                    "UPDATE jobs SET state = 'QUEUED', claimed_at = NULL, updated_at = ? "
                    "WHERE state IN ('CLAIMED', 'RUNNING')",
                    (ts,),
                )
            else:
                cur = self._conn.execute(
                    "UPDATE jobs SET state = 'QUEUED', claimed_at = NULL, updated_at = ? "
                    "WHERE state IN ('CLAIMED', 'RUNNING') "
                    "AND (claimed_at IS NULL OR claimed_at < ?)",
                    (ts, stale_before),
                )
        return cur.rowcount

    def list_jobs_by_state(self, state: str) -> list[dict]:
        """Infrastructure/observability read across accounts."""
        cur = self._conn.execute(
            "SELECT * FROM jobs WHERE state = ? ORDER BY created_at, job_id", (state,)
        )
        return [dict(r) for r in cur.fetchall()]

    def count_jobs_by_state(self) -> dict:
        cur = self._conn.execute("SELECT state, COUNT(*) c FROM jobs GROUP BY state")
        return {r["state"]: r["c"] for r in cur.fetchall()}


def open_store(path: str) -> Store:
    """Connect, migrate, and return a Store."""
    conn = db.connect(path)
    db.migrate(conn)
    return Store(conn)
