"""Durable persistence for council-mcp (Phase 1D), standard-library sqlite3 only.

  * db         — connection factory (WAL, foreign keys) + migration runner
  * migrations — ordered schema migrations (tracked via PRAGMA user_version)
  * repo       — Store: account-scoped operations over the schema

Security invariant enforced HERE, not at call sites: every read and write is
filtered by account_id. A row owned by account A is invisible and immutable to
account B. See repo.Store.
"""

from .repo import Store, open_store

__all__ = ["Store", "open_store"]
