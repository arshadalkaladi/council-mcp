"""Engine flow: completion, audit trail, cancellation, failure containment,
FAILED path, restart resume, determinism, and account isolation."""

import os
import tempfile
import unittest

from council_mcp.council.engine import run_deliberation
from council_mcp.council.provider import DeterministicDemoProvider
from council_mcp.council.perspectives import PERSPECTIVES
from council_mcp.store import open_store

PROVIDER = DeterministicDemoProvider()


def job(account, did):
    return {"account_id": account, "ref_id": did, "job_id": "j", "kind": "deliberation"}


class EngineTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.store = open_store(os.path.join(self.dir, "e.db"))

    def tearDown(self):
        self.store.close()

    def _seed(self, account="acct-A", did="d1", q="move or stay?"):
        self.store.create_deliberation(account, did, q, status="QUEUED")

    def test_full_flow_to_completed(self):
        self._seed()
        run_deliberation(job("acct-A", "d1"), self.store, PROVIDER)
        d = self.store.get_deliberation("acct-A", "d1")
        self.assertEqual(d["status"], "COMPLETED")
        self.assertEqual(d["partial"], 0)
        # all perspectives recorded
        persp = self.store.list_perspective_results("acct-A", "d1")
        self.assertEqual(len(persp), len(PERSPECTIVES))
        # synthesis present
        synth = self.store.get_synthesis("acct-A", "d1")
        self.assertIsNotNone(synth)
        self.assertIn(synth["recommendation"], ("support", "oppose", "conditional"))
        # audit trail contains lifecycle
        types = [e["type"] for e in self.store.list_audit("acct-A", "d1")]
        self.assertIn("running", types)
        self.assertIn("synthesizing", types)
        self.assertIn("completed", types)

    def test_deterministic_reproducibility(self):
        self._seed(did="d1")
        self._seed(did="d2")
        run_deliberation(job("acct-A", "d1"), self.store, PROVIDER)
        run_deliberation(job("acct-A", "d2"), self.store, PROVIDER)
        s1 = self.store.get_synthesis("acct-A", "d1")
        s2 = self.store.get_synthesis("acct-A", "d2")
        self.assertEqual(s1["recommendation"], s2["recommendation"])
        self.assertEqual(s1["confidence"], s2["confidence"])
        self.assertEqual(s1["dissents"], s2["dissents"])

    def test_cancel_before_run_stays_cancelled(self):
        self._seed()
        self.assertTrue(self.store.cancel_deliberation("acct-A", "d1"))
        run_deliberation(job("acct-A", "d1"), self.store, PROVIDER)
        self.assertEqual(self.store.get_deliberation("acct-A", "d1")["status"], "CANCELLED")
        # No perspectives were computed.
        self.assertEqual(self.store.list_perspective_results("acct-A", "d1"), [])

    def test_cancel_mid_run_stops_cleanly(self):
        self._seed()
        store = self.store

        class CancelAfterFirst(DeterministicDemoProvider):
            def __init__(self):
                self.calls = 0

            def analyze(self, question, perspective, description):
                self.calls += 1
                out = super().analyze(question, perspective, description)
                if self.calls == 1:
                    store.cancel_deliberation("acct-A", "d1")  # cancel mid-run
                return out

        run_deliberation(job("acct-A", "d1"), self.store, CancelAfterFirst())
        d = self.store.get_deliberation("acct-A", "d1")
        self.assertEqual(d["status"], "CANCELLED")
        # It stopped early: fewer than the full set of perspectives ran.
        self.assertLess(len(self.store.list_perspective_results("acct-A", "d1")),
                        len(PERSPECTIVES))

    def test_perspective_failure_is_contained_partial(self):
        self._seed()

        class OneFails(DeterministicDemoProvider):
            def analyze(self, question, perspective, description):
                if perspective == "risk":
                    raise RuntimeError("provider blip")
                return super().analyze(question, perspective, description)

        run_deliberation(job("acct-A", "d1"), self.store, OneFails())
        d = self.store.get_deliberation("acct-A", "d1")
        self.assertEqual(d["status"], "COMPLETED")
        self.assertEqual(d["partial"], 1)
        results = self.store.list_perspective_results("acct-A", "d1")
        failed = [r for r in results if r["failed"]]
        self.assertEqual(len(failed), 1)
        self.assertEqual(failed[0]["perspective"], "risk")

    def test_unexpected_error_marks_failed_and_raises(self):
        self._seed()

        class BrokenStore:
            # Delegate everything to the real store, but blow up at save_synthesis.
            def __init__(self, real):
                self._real = real

            def __getattr__(self, name):
                return getattr(self._real, name)

            def save_synthesis(self, *a, **k):
                raise RuntimeError("disk exploded")

        broken = BrokenStore(self.store)
        with self.assertRaises(RuntimeError):
            run_deliberation(job("acct-A", "d1"), broken, PROVIDER)
        self.assertEqual(self.store.get_deliberation("acct-A", "d1")["status"], "FAILED")

    def test_resume_from_running_is_idempotent(self):
        # Simulate a crash mid-flight: RUNNING with 2 perspectives already saved.
        self._seed()
        self.store.update_deliberation_status("acct-A", "d1", "RUNNING",
                                              expected_status="QUEUED")
        for name, _ in PERSPECTIVES[:2]:
            self.store.save_perspective_result("acct-A", "d1", name,
                                               stance="support", confidence=0.8)
        # Re-run (as the worker would after recovery).
        run_deliberation(job("acct-A", "d1"), self.store, PROVIDER)
        d = self.store.get_deliberation("acct-A", "d1")
        self.assertEqual(d["status"], "COMPLETED")
        # No duplicate perspectives: exactly one row per perspective.
        results = self.store.list_perspective_results("acct-A", "d1")
        names = [r["perspective"] for r in results]
        self.assertEqual(sorted(names), sorted(n for n, _ in PERSPECTIVES))

    def test_account_isolation(self):
        self._seed(account="acct-A", did="d1")
        run_deliberation(job("acct-A", "d1"), self.store, PROVIDER)
        # A different account sees nothing.
        self.assertIsNone(self.store.get_deliberation("acct-B", "d1"))
        self.assertIsNone(self.store.get_synthesis("acct-B", "d1"))
        self.assertEqual(self.store.list_perspective_results("acct-B", "d1"), [])


if __name__ == "__main__":
    unittest.main()
