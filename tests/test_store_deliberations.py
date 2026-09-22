"""Store CRUD, atomic updates, audit, and account scoping."""

import os
import tempfile
import unittest

from council_mcp.store import open_store
from council_mcp.store.repo import DuplicateError

TS = "2026-01-01T00:00:00+00:00"


class StoreDeliberationTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.store = open_store(os.path.join(self.dir, "t.db"))

    def tearDown(self):
        self.store.close()

    def test_create_get_list(self):
        self.store.create_deliberation("acct-A", "d1", "move or stay?", now=TS)
        row = self.store.get_deliberation("acct-A", "d1")
        self.assertEqual(row["question"], "move or stay?")
        self.assertEqual(row["status"], "QUEUED")
        self.assertEqual(row["partial"], 0)
        self.assertEqual(len(self.store.list_deliberations("acct-A")), 1)

    def test_duplicate_rejected(self):
        self.store.create_deliberation("acct-A", "d1", "q", now=TS)
        with self.assertRaises(DuplicateError):
            self.store.create_deliberation("acct-A", "d1", "q2", now=TS)

    def test_atomic_status_update(self):
        self.store.create_deliberation("acct-A", "d1", "q", now=TS)
        ok = self.store.update_deliberation_status("acct-A", "d1", "RUNNING")
        self.assertTrue(ok)
        self.assertEqual(self.store.get_deliberation("acct-A", "d1")["status"], "RUNNING")

    def test_optimistic_guard(self):
        self.store.create_deliberation("acct-A", "d1", "q", now=TS)
        # Guard fails when the expected status doesn't match current.
        self.assertFalse(
            self.store.update_deliberation_status(
                "acct-A", "d1", "COMPLETED", expected_status="RUNNING")
        )
        self.assertEqual(self.store.get_deliberation("acct-A", "d1")["status"], "QUEUED")
        # Guard succeeds when it matches.
        self.assertTrue(
            self.store.update_deliberation_status(
                "acct-A", "d1", "RUNNING", expected_status="QUEUED")
        )

    def test_terminal_sets_terminal_at(self):
        self.store.create_deliberation("acct-A", "d1", "q", now=TS)
        self.store.update_deliberation_status("acct-A", "d1", "COMPLETED", terminal=True)
        row = self.store.get_deliberation("acct-A", "d1")
        self.assertIsNotNone(row["terminal_at"])

    def test_audit_append_and_list(self):
        self.store.create_deliberation("acct-A", "d1", "q", now=TS)
        eid = self.store.append_audit("acct-A", "d1", "created", "queued", now=TS)
        self.assertIsNotNone(eid)
        events = self.store.list_audit("acct-A", "d1")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["type"], "created")

    def test_jobs_roundtrip(self):
        job = self.store.create_job("acct-A", "j1", "deliberation", "d1", now=TS)
        self.assertEqual(job["state"], "QUEUED")
        self.assertEqual(job["attempts"], 0)
        self.assertEqual(self.store.get_job("acct-A", "j1")["ref_id"], "d1")


if __name__ == "__main__":
    unittest.main()
