"""Provider determinism and synthesis logic (no store)."""

import unittest

from council_mcp.council.provider import DeterministicDemoProvider
from council_mcp.council.synthesis import synthesize


class ProviderTest(unittest.TestCase):
    def test_deterministic_same_input_same_output(self):
        p = DeterministicDemoProvider()
        a = p.analyze("move or stay?", "risk", "surfaces downside")
        b = p.analyze("move or stay?", "risk", "surfaces downside")
        self.assertEqual(a, b)

    def test_different_perspective_differs(self):
        p = DeterministicDemoProvider()
        a = p.analyze("q", "risk", "d")
        b = p.analyze("q", "practical", "d")
        self.assertNotEqual((a.stance, a.argument), (b.stance, b.argument))

    def test_confidence_in_range_and_evidence_shape(self):
        p = DeterministicDemoProvider()
        o = p.analyze("q", "evidence", "d")
        self.assertGreaterEqual(o.confidence, 0.0)
        self.assertLessEqual(o.confidence, 1.0)
        self.assertEqual(len(o.evidence), 2)
        self.assertIn("claim", o.evidence[0])


class SynthesisTest(unittest.TestCase):
    def test_preserves_dissent(self):
        results = [
            {"perspective": "a", "stance": "support", "confidence": 0.9, "failed": False},
            {"perspective": "b", "stance": "oppose", "confidence": 0.6, "failed": False},
            {"perspective": "c", "stance": "support", "confidence": 0.7, "failed": False},
        ]
        s = synthesize(results)
        self.assertEqual(s["recommendation"], "support")  # 1.6 vs 0.6 weight
        self.assertEqual([d["perspective"] for d in s["dissents"]], ["b"])
        self.assertEqual(s["considered"], ["a", "b", "c"])

    def test_all_failed_is_inconclusive(self):
        results = [{"perspective": "a", "stance": None, "confidence": None, "failed": True}]
        s = synthesize(results)
        self.assertEqual(s["recommendation"], "inconclusive")
        self.assertEqual(s["confidence"], 0.0)

    def test_partial_uses_only_usable(self):
        results = [
            {"perspective": "a", "stance": "oppose", "confidence": 0.8, "failed": False},
            {"perspective": "b", "stance": None, "confidence": None, "failed": True},
        ]
        s = synthesize(results)
        self.assertEqual(s["recommendation"], "oppose")
        self.assertEqual(s["considered"], ["a", "b"])  # b still 'considered'


if __name__ == "__main__":
    unittest.main()
