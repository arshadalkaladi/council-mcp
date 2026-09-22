"""Smoke test: the canonical deterministic demo completes a deliberation.

Keeps the demo covered by the regression suite so it never silently rots.
"""

import importlib.util
import os
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEMO = os.path.join(_ROOT, "demo", "deterministic_demo.py")

_spec = importlib.util.spec_from_file_location("deterministic_demo", _DEMO)
_demo = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_demo)


class DemoSmokeTest(unittest.TestCase):
    def test_demo_completes(self):
        out = _demo.run_demo(quiet=True)
        r = out["result"]
        self.assertEqual(r["status"], "COMPLETED")
        self.assertIsNotNone(r["synthesis"])
        self.assertEqual(len(r["perspectives"]), 4)
        self.assertLess(out["elapsed"], 30.0)

    def test_demo_is_reproducible(self):
        a = _demo.run_demo(quiet=True)["result"]["synthesis"]
        b = _demo.run_demo(quiet=True)["result"]["synthesis"]
        self.assertEqual(a["recommendation"], b["recommendation"])
        self.assertEqual(a["confidence"], b["confidence"])


if __name__ == "__main__":
    unittest.main()
