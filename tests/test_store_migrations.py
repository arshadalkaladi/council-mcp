"""Migration runner tests."""

import os
import tempfile
import unittest

from council_mcp.store import db


class MigrationTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "t.db")

    def _tables(self, conn):
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        return {r[0] for r in rows}

    def test_migrate_creates_schema_and_sets_version(self):
        conn = db.connect(self.path)
        version = db.migrate(conn)
        self.assertGreaterEqual(version, 1)
        tables = self._tables(conn)
        for t in ("deliberations", "perspective_results", "synthesis",
                  "audit_events", "jobs"):
            self.assertIn(t, tables)
        conn.close()

    def test_migrate_is_idempotent(self):
        conn = db.connect(self.path)
        v1 = db.migrate(conn)
        v2 = db.migrate(conn)  # running again must not error or duplicate
        self.assertEqual(v1, v2)
        conn.close()

    def test_wal_mode_enabled(self):
        conn = db.connect(self.path)
        db.migrate(conn)
        self.assertEqual(db.journal_mode(conn).lower(), "wal")
        conn.close()


if __name__ == "__main__":
    unittest.main()
