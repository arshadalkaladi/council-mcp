"""CouncilService with a live WorkerPool: start -> completed, cancel, and
restart recovery of a mid-flight deliberation."""

import os
import tempfile
import time
import unittest

from council_mcp.council import CouncilService, DeterministicDemoProvider, run_deliberation
from council_mcp.jobs import WorkerPool
from council_mcp.store import open_store


def wait_for(fn, timeout=8.0, interval=0.02):
    end = time.time() + timeout
    while time.time() < end:
        if fn():
            return True
        time.sleep(interval)
    return fn()


class CouncilServiceTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "svc.db")
        open_store(self.path).close()  # migrate once
        self.provider = DeterministicDemoProvider()
        self.service = CouncilService(self.path)  # migrate=False (already migrated)
        self.pool = WorkerPool(
            self.path,
            {"deliberation": lambda job, store: run_deliberation(job, store, self.provider)},
            concurrency=2,
        )

    def tearDown(self):
        self.pool.stop()

    def test_start_to_completed(self):
        started = self.service.start("acct-A", "Should I move or stay?")
        did = started["deliberation_id"]
        self.assertEqual(started["status"], "QUEUED")
        self.pool.start()
        ok = wait_for(lambda: self.service.get("acct-A", did)["status"] == "COMPLETED")
        self.assertTrue(ok)
        result = self.service.get("acct-A", did)
        self.assertIsNotNone(result["synthesis"])
        self.assertEqual(len(result["perspectives"]), 4)
        self.assertIn("completed", [e["type"] for e in result["audit"]])

    def test_cancel_queued(self):
        # Do not start the pool: the deliberation stays QUEUED and is cancellable.
        started = self.service.start("acct-A", "q")
        did = started["deliberation_id"]
        res = self.service.cancel("acct-A", did)
        self.assertEqual(res["status"], "CANCELLED")
        self.assertEqual(self.service.get("acct-A", did)["status"], "CANCELLED")

    def test_get_unknown_returns_none(self):
        self.assertIsNone(self.service.get("acct-A", "nope"))

    def test_cancel_unknown_not_cancellable(self):
        self.assertIn("error", self.service.cancel("acct-A", "nope"))

    def test_account_isolation_via_service(self):
        started = self.service.start("acct-A", "q")
        did = started["deliberation_id"]
        self.assertIsNone(self.service.get("acct-B", did))
        self.assertIn("error", self.service.cancel("acct-B", did))

    def test_restart_recovery_completes(self):
        # Simulate a crash: deliberation RUNNING, its job left CLAIMED.
        s = open_store(self.path)
        s.create_deliberation("acct-A", "dR", "q", status="QUEUED")
        s.create_job("acct-A", "jR", "deliberation", "dR")
        s.claim_next_job()  # CLAIMED (job in-flight)
        s.update_deliberation_status("acct-A", "dR", "RUNNING", expected_status="QUEUED")
        s.close()
        # New worker recovers the stale job and the engine resumes to COMPLETED.
        self.pool.start(recover=True)
        ok = wait_for(lambda: self.service.get("acct-A", "dR")["status"] == "COMPLETED")
        self.assertTrue(ok)


if __name__ == "__main__":
    unittest.main()
