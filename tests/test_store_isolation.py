"""Cross-account isolation is enforced at the store layer."""

import os
import tempfile
import unittest

from council_mcp.store import open_store

TS = "2026-01-01T00:00:00+00:00"


class StoreIsolationTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.store = open_store(os.path.join(self.dir, "t.db"))
        # Account A owns d1.
        self.store.create_deliberation("acct-A", "d1", "A's question", now=TS)
        self.store.create_job("acct-A", "j1", "deliberation", "d1", now=TS)

    def tearDown(self):
        self.store.close()

    def test_foreign_account_cannot_read(self):
        self.assertIsNone(self.store.get_deliberation("acct-B", "d1"))
        self.assertIsNone(self.store.get_job("acct-B", "j1"))
        self.assertEqual(self.store.list_deliberations("acct-B"), [])

    def test_foreign_account_cannot_update(self):
        changed = self.store.update_deliberation_status("acct-B", "d1", "RUNNING")
        self.assertFalse(changed)
        # A's record is untouched.
        self.assertEqual(self.store.get_deliberation("acct-A", "d1")["status"], "QUEUED")

    def test_foreign_account_cannot_append_audit(self):
        eid = self.store.append_audit("acct-B", "d1", "tamper", "nope")
        self.assertIsNone(eid)
        self.assertEqual(self.store.list_audit("acct-A", "d1"), [])
        self.assertEqual(self.store.list_audit("acct-B", "d1"), [])

    def test_owner_still_has_access(self):
        self.assertIsNotNone(self.store.get_deliberation("acct-A", "d1"))
        self.assertTrue(self.store.update_deliberation_status("acct-A", "d1", "RUNNING"))


if __name__ == "__main__":
    unittest.main()
