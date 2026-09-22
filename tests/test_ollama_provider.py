"""OllamaProvider with an injected transport: parsing, bounds, and safe
fallback. No real network is used."""

import json
import os
import tempfile
import unittest

from council_mcp.council.ollama_provider import FallbackProvider, OllamaProvider
from council_mcp.council.provider import DeterministicDemoProvider
from council_mcp.council.engine import run_deliberation
from council_mcp.council.perspectives import PERSPECTIVES
from council_mcp.store import open_store


class _FakeResp:
    def __init__(self, body: bytes):
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self, n=-1):
        return self._body if n < 0 else self._body[:n]


def _ollama_body(stance="support", confidence=0.8, argument="because reasons"):
    inner = json.dumps({"stance": stance, "confidence": confidence, "argument": argument})
    return json.dumps({"response": inner}).encode("utf-8")


def fake_ok(*args, **kwargs):
    return _FakeResp(_ollama_body())


class OllamaProviderTest(unittest.TestCase):
    def test_parses_valid_response(self):
        p = OllamaProvider("http://x", "m", urlopen=fake_ok)
        out = p.analyze("q", "risk", "d")
        self.assertEqual(out.stance, "support")
        self.assertEqual(out.confidence, 0.8)
        self.assertTrue(out.argument)
        self.assertEqual(out.evidence[0]["source_kind"], "model")

    def test_invalid_stance_raises(self):
        def bad(*a, **k):
            return _FakeResp(_ollama_body(stance="maybe"))
        with self.assertRaises(ValueError):
            OllamaProvider("http://x", "m", urlopen=bad).analyze("q", "p", "d")

    def test_oversize_response_raises(self):
        big = json.dumps({"response": json.dumps({"stance": "support",
                          "confidence": 0.5, "argument": "x" * 100})}).encode()

        def huge(*a, **k):
            return _FakeResp(big)
        p = OllamaProvider("http://x", "m", urlopen=huge, max_bytes=10)
        with self.assertRaises(ValueError):
            p.analyze("q", "p", "d")

    def test_connection_error_raises(self):
        def boom(*a, **k):
            raise OSError("connection refused")
        with self.assertRaises(OSError):
            OllamaProvider("http://x", "m", urlopen=boom).analyze("q", "p", "d")

    def test_confidence_clamped(self):
        def over(*a, **k):
            return _FakeResp(_ollama_body(confidence=5.0))
        out = OllamaProvider("http://x", "m", urlopen=over).analyze("q", "p", "d")
        self.assertLessEqual(out.confidence, 1.0)


class FallbackProviderTest(unittest.TestCase):
    def test_uses_primary_when_ok(self):
        primary = OllamaProvider("http://x", "m", urlopen=fake_ok)
        fp = FallbackProvider(primary, DeterministicDemoProvider())
        out = fp.analyze("q", "risk", "d")
        self.assertEqual(out.evidence[0]["source_kind"], "model")  # came from primary

    def test_falls_back_on_error(self):
        def boom(*a, **k):
            raise OSError("down")
        primary = OllamaProvider("http://x", "m", urlopen=boom)
        deterministic = DeterministicDemoProvider()
        fp = FallbackProvider(primary, deterministic)
        out = fp.analyze("q", "risk", "d")
        # Identical to what the deterministic provider would have produced.
        self.assertEqual(out, deterministic.analyze("q", "risk", "d"))


class OptionalProviderThroughEngineTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.store = open_store(os.path.join(self.dir, "o.db"))

    def tearDown(self):
        self.store.close()

    def _job(self, did):
        return {"account_id": "acct-A", "ref_id": did, "job_id": "j", "kind": "deliberation"}

    def test_optional_provider_completes_full_deliberation(self):
        self.store.create_deliberation("acct-A", "d1", "q", status="QUEUED")
        provider = OllamaProvider("http://x", "m", urlopen=fake_ok)
        run_deliberation(self._job("d1"), self.store, provider)
        d = self.store.get_deliberation("acct-A", "d1")
        self.assertEqual(d["status"], "COMPLETED")
        results = self.store.list_perspective_results("acct-A", "d1")
        self.assertEqual(len(results), len(PERSPECTIVES))
        # Every perspective used the model transport.
        self.assertTrue(all(r["evidence"][0]["source_kind"] == "model" for r in results))

    def test_fallback_deliberation_matches_deterministic(self):
        def boom(*a, **k):
            raise OSError("down")
        self.store.create_deliberation("acct-A", "dfb", "q", status="QUEUED")
        provider = FallbackProvider(OllamaProvider("http://x", "m", urlopen=boom),
                                    DeterministicDemoProvider())
        run_deliberation(self._job("dfb"), self.store, provider)

        # Compare with a pure-deterministic run of the same question.
        self.store.create_deliberation("acct-A", "ddet", "q", status="QUEUED")
        run_deliberation(self._job("ddet"), self.store, DeterministicDemoProvider())

        s_fb = self.store.get_synthesis("acct-A", "dfb")
        s_det = self.store.get_synthesis("acct-A", "ddet")
        self.assertEqual(s_fb["recommendation"], s_det["recommendation"])
        self.assertEqual(s_fb["confidence"], s_det["confidence"])
        self.assertEqual(s_fb["dissents"], s_det["dissents"])


if __name__ == "__main__":
    unittest.main()
