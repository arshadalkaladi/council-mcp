"""Deterministic store-level job mechanics: claim, retry, dead, recovery,
concurrent-claim safety, and account isolation of user reads."""

import os
import tempfile
import threading
import unittest

from council_mcp.store import open_store

TS = "2026-01-01T00:00:00+00:00"


class JobsStoreTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "jobs.db")
        self.store = open_store(self.path)

    def tearDown(self):
        self.store.close()

    def test_claim_transitions_queued_to_claimed(self):
        self.store.create_job("acct-A", "j1", "noop", "r1", now=TS)
        claimed = self.store.claim_next_job()
        self.assertEqual(claimed["job_id"], "j1")
        self.assertEqual(claimed["state"], "CLAIMED")
        # No more queued jobs.
        self.assertIsNone(self.store.claim_next_job())

    def test_success_flow(self):
        self.store.create_job("acct-A", "j1", "noop", "r1", now=TS)
        self.store.claim_next_job()
        self.assertTrue(self.store.mark_job_running("j1"))
        self.assertTrue(self.store.mark_job_succeeded("j1"))
        self.assertEqual(self.store.get_job("acct-A", "j1")["state"], "SUCCEEDED")

    def test_retry_then_dead(self):
        self.store.create_job("acct-A", "j1", "noop", "r1", max_attempts=2, now=TS)
        # First failure -> requeued.
        self.store.claim_next_job()
        self.store.mark_job_running("j1")
        self.assertEqual(self.store.mark_job_failed("j1", "boom"), "QUEUED")
        self.assertEqual(self.store.get_job("acct-A", "j1")["attempts"], 1)
        # Second failure -> DEAD (attempts == max_attempts).
        self.store.claim_next_job()
        self.store.mark_job_running("j1")
        self.assertEqual(self.store.mark_job_failed("j1", "boom"), "DEAD")
        row = self.store.get_job("acct-A", "j1")
        self.assertEqual(row["state"], "DEAD")
        self.assertEqual(row["attempts"], 2)

    def test_recover_stale_jobs(self):
        self.store.create_job("acct-A", "j1", "noop", "r1", now=TS)
        self.store.claim_next_job()  # -> CLAIMED (simulate crash mid-flight)
        self.store.mark_job_running("j1")  # -> RUNNING
        recovered = self.store.recover_stale_jobs()
        self.assertEqual(recovered, 1)
        row = self.store.get_job("acct-A", "j1")
        self.assertEqual(row["state"], "QUEUED")
        self.assertIsNone(row["claimed_at"])

    def test_mark_failed_ignores_non_inflight(self):
        self.store.create_job("acct-A", "j1", "noop", "r1", now=TS)
        # Not claimed yet (QUEUED) -> not transitionable.
        self.assertIsNone(self.store.mark_job_failed("j1", "x"))

    def test_user_get_job_is_account_scoped(self):
        self.store.create_job("acct-A", "j1", "noop", "r1", now=TS)
        self.assertIsNone(self.store.get_job("acct-B", "j1"))
        self.assertIsNotNone(self.store.get_job("acct-A", "j1"))

    def test_concurrent_claim_no_double_execution(self):
        n = 60
        for i in range(n):
            self.store.create_job("acct-A", f"j{i}", "noop", f"r{i}", now=TS)

        claimed: list[str] = []
        lock = threading.Lock()

        def worker():
            s = open_store(self.path)  # own connection per thread
            try:
                while True:
                    job = s.claim_next_job()
                    if job is None:
                        return
                    with lock:
                        claimed.append(job["job_id"])
            finally:
                s.close()

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        # Every job claimed exactly once (no duplicates, none missed).
        self.assertEqual(len(claimed), n)
        self.assertEqual(len(set(claimed)), n)


if __name__ == "__main__":
    unittest.main()
