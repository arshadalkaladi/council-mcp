"""Data survives closing and reopening the database (process-restart proxy)."""

import os
import tempfile
import unittest

from council_mcp.store import open_store

TS = "2026-01-01T00:00:00+00:00"


class StoreRestartTest(unittest.TestCase):
    def test_data_persists_across_reopen(self):
        d = tempfile.mkdtemp()
        path = os.path.join(d, "restart.db")

        # First "process": write and close.
        s1 = open_store(path)
        s1.create_deliberation("acct-A", "d1", "durable?", status="RUNNING", now=TS)
        s1.append_audit("acct-A", "d1", "created", now=TS)
        s1.create_job("acct-A", "j1", "deliberation", "d1", now=TS)
        s1.close()

        # Second "process": reopen (migrate is idempotent) and read back.
        s2 = open_store(path)
        row = s2.get_deliberation("acct-A", "d1")
        self.assertIsNotNone(row)
        self.assertEqual(row["question"], "durable?")
        self.assertEqual(row["status"], "RUNNING")
        self.assertEqual(len(s2.list_audit("acct-A", "d1")), 1)
        self.assertIsNotNone(s2.get_job("acct-A", "j1"))
        s2.close()

    def test_update_persists_across_reopen(self):
        d = tempfile.mkdtemp()
        path = os.path.join(d, "restart2.db")
        s1 = open_store(path)
        s1.create_deliberation("acct-A", "d1", "q", now=TS)
        s1.update_deliberation_status("acct-A", "d1", "COMPLETED", terminal=True, now=TS)
        s1.close()

        s2 = open_store(path)
        row = s2.get_deliberation("acct-A", "d1")
        self.assertEqual(row["status"], "COMPLETED")
        self.assertIsNotNone(row["terminal_at"])
        s2.close()


if __name__ == "__main__":
    unittest.main()
