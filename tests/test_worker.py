"""WorkerPool integration: success, retry->DEAD, wall-clock budget, graceful
shutdown, account isolation, and real account-scoped handler work."""

import os
import tempfile
import time
import unittest

from council_mcp.jobs import WorkerPool
from council_mcp.store import open_store

TS = "2026-01-01T00:00:00+00:00"


def wait_for(predicate, timeout=8.0, interval=0.02):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return predicate()


class WorkerPoolTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "w.db")
        self.seed = open_store(self.path)
        self.inspect = open_store(self.path)

    def tearDown(self):
        self.seed.close()
        self.inspect.close()

    def _state(self, account, job_id):
        return self.inspect.get_job(account, job_id)["state"]

    def test_success_processing(self):
        for i in range(5):
            self.seed.create_job("acct-A", f"j{i}", "noop", f"r{i}", now=TS)
        pool = WorkerPool(self.path, {"noop": lambda job, store: None}, concurrency=3)
        pool.start()
        try:
            ok = wait_for(lambda: self.inspect.count_jobs_by_state().get("SUCCEEDED", 0) == 5)
        finally:
            pool.stop()
        self.assertTrue(ok, self.inspect.count_jobs_by_state())

    def test_failing_handler_goes_dead(self):
        self.seed.create_job("acct-A", "jf", "boom", "r", max_attempts=2, now=TS)

        def boom(job, store):
            raise RuntimeError("intentional")

        pool = WorkerPool(self.path, {"boom": boom}, concurrency=1)
        pool.start()
        try:
            ok = wait_for(lambda: self._state("acct-A", "jf") == "DEAD")
        finally:
            pool.stop()
        self.assertTrue(ok)
        self.assertEqual(self.inspect.get_job("acct-A", "jf")["attempts"], 2)

    def test_wall_clock_budget(self):
        self.seed.create_job("acct-A", "jslow", "slow", "r", max_attempts=1, now=TS)

        def slow(job, store):
            time.sleep(3.0)  # far exceeds the budget

        pool = WorkerPool(self.path, {"slow": slow}, concurrency=1,
                          job_budget_seconds=0.2)
        pool.start()
        try:
            # Budget is 0.2s and max_attempts=1, so it should be DEAD quickly.
            ok = wait_for(lambda: self._state("acct-A", "jslow") == "DEAD", timeout=3.0)
        finally:
            pool.stop()
        self.assertTrue(ok)
        self.assertEqual(self.inspect.get_job("acct-A", "jslow")["error"],
                         "wall_clock_budget_exceeded")

    def test_graceful_shutdown_joins_threads(self):
        pool = WorkerPool(self.path, {"noop": lambda j, s: None}, concurrency=2)
        pool.start()
        self.assertEqual(len(pool._threads), 2)
        pool.stop()
        self.assertEqual(pool._threads, [])

    def test_account_isolation_across_worker(self):
        self.seed.create_job("acct-A", "ja", "noop", "ra", now=TS)
        self.seed.create_job("acct-B", "jb", "noop", "rb", now=TS)
        pool = WorkerPool(self.path, {"noop": lambda j, s: None}, concurrency=2)
        pool.start()
        try:
            wait_for(lambda: self.inspect.count_jobs_by_state().get("SUCCEEDED", 0) == 2)
        finally:
            pool.stop()
        # User-facing reads remain account-scoped even though the worker
        # (infrastructure) processed both.
        self.assertIsNone(self.inspect.get_job("acct-A", "jb"))
        self.assertIsNone(self.inspect.get_job("acct-B", "ja"))
        self.assertEqual(self._state("acct-A", "ja"), "SUCCEEDED")
        self.assertEqual(self._state("acct-B", "jb"), "SUCCEEDED")

    def test_handler_does_account_scoped_work(self):
        self.seed.create_job("acct-A", "jw", "make", "delib-1", now=TS)

        def make(job, store):
            store.create_deliberation(job["account_id"], job["ref_id"],
                                      "from worker", status="COMPLETED")
            store.append_audit(job["account_id"], job["ref_id"], "worker_done")

        pool = WorkerPool(self.path, {"make": make}, concurrency=1)
        pool.start()
        try:
            wait_for(lambda: self._state("acct-A", "jw") == "SUCCEEDED")
        finally:
            pool.stop()
        d = self.inspect.get_deliberation("acct-A", "delib-1")
        self.assertIsNotNone(d)
        self.assertEqual(d["status"], "COMPLETED")
        self.assertEqual(len(self.inspect.list_audit("acct-A", "delib-1")), 1)
        # The work belongs to acct-A only.
        self.assertIsNone(self.inspect.get_deliberation("acct-B", "delib-1"))


class WorkerRestartRecoveryTest(unittest.TestCase):
    def test_stale_job_recovered_and_processed(self):
        d = tempfile.mkdtemp()
        path = os.path.join(d, "r.db")
        s = open_store(path)
        s.create_job("acct-A", "j1", "noop", "r1", now=TS)
        s.claim_next_job()          # CLAIMED
        s.mark_job_running("j1")    # RUNNING (simulate crash here)
        s.close()

        # New pool starts, recovers the stale RUNNING job, then processes it.
        pool = WorkerPool(path, {"noop": lambda j, st: None}, concurrency=1)
        pool.start(recover=True)
        try:
            inspect = open_store(path)
            ok = wait_for(lambda: inspect.get_job("acct-A", "j1")["state"] == "SUCCEEDED")
        finally:
            pool.stop()
            inspect.close()
        self.assertTrue(ok)


if __name__ == "__main__":
    unittest.main()
