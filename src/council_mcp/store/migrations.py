"""Ordered schema migrations.

Each entry is a SQL script applied once, in order; the applied count is stored
in PRAGMA user_version. Append new migrations; never edit an applied one.

Schema mirrors the frozen Concept-A data model: deliberations, per-perspective
results, synthesis, audit events, and background jobs. Every table carries
account_id so the store can scope every query to the caller.
"""

from __future__ import annotations

_MIGRATION_1 = """
CREATE TABLE deliberations (
    deliberation_id TEXT PRIMARY KEY,
    account_id      TEXT NOT NULL,
    question        TEXT NOT NULL,
    status          TEXT NOT NULL,
    partial         INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    terminal_at     TEXT
);
CREATE INDEX idx_delib_account ON deliberations(account_id);

CREATE TABLE perspective_results (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    deliberation_id TEXT NOT NULL,
    account_id      TEXT NOT NULL,
    perspective     TEXT NOT NULL,
    stance          TEXT,
    argument        TEXT,
    confidence      REAL,
    evidence_json   TEXT,
    failed          INTEGER NOT NULL DEFAULT 0,
    error           TEXT,
    created_at      TEXT NOT NULL,
    FOREIGN KEY (deliberation_id)
        REFERENCES deliberations (deliberation_id) ON DELETE CASCADE
);
CREATE INDEX idx_persp_delib ON perspective_results(deliberation_id);

CREATE TABLE synthesis (
    deliberation_id TEXT PRIMARY KEY,
    account_id      TEXT NOT NULL,
    recommendation  TEXT,
    rationale       TEXT,
    confidence      REAL,
    considered_json TEXT,
    dissents_json   TEXT,
    created_at      TEXT NOT NULL,
    FOREIGN KEY (deliberation_id)
        REFERENCES deliberations (deliberation_id) ON DELETE CASCADE
);

CREATE TABLE audit_events (
    event_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    deliberation_id TEXT NOT NULL,
    account_id      TEXT NOT NULL,
    ts              TEXT NOT NULL,
    type            TEXT NOT NULL,
    detail          TEXT,
    FOREIGN KEY (deliberation_id)
        REFERENCES deliberations (deliberation_id) ON DELETE CASCADE
);
CREATE INDEX idx_audit_delib ON audit_events(deliberation_id);

CREATE TABLE jobs (
    job_id       TEXT PRIMARY KEY,
    account_id   TEXT NOT NULL,
    kind         TEXT NOT NULL,
    ref_id       TEXT NOT NULL,
    state        TEXT NOT NULL,
    attempts     INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    claimed_at   TEXT,
    error        TEXT,
    created_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL
);
CREATE INDEX idx_jobs_state ON jobs(state);
CREATE INDEX idx_jobs_account ON jobs(account_id);
"""

# Ordered; index+1 is the version each migration establishes.
MIGRATIONS = [_MIGRATION_1]
