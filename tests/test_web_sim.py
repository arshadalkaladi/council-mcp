"""Smoke test for the web simulation harness: it drives a real deliberation
through the certified MCP flow and its /api/* endpoints work."""

import importlib.util
import json
import os
import time
import unittest
import urllib.request

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_WS = os.path.join(_ROOT, "demo", "web_sim.py")
_spec = importlib.util.spec_from_file_location("web_sim", _WS)
web_sim = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(web_sim)


class WebSimTest(unittest.TestCase):
    def setUp(self):
        self.sim = web_sim.WebSim(sim_port=0).start()
        self.base = f"http://127.0.0.1:{self.sim.sim_port}"

    def tearDown(self):
        self.sim.stop()

    def test_index_served(self):
        with urllib.request.urlopen(self.base + "/", timeout=5) as r:
            html = r.read().decode()
        self.assertIn("Deliberation Council", html)

    def test_api_start_and_status_complete(self):
        # start
        req = urllib.request.Request(self.base + "/api/start",
                                     data=json.dumps({"question": "web sim?"}).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=5) as r:
            started = json.loads(r.read())
        did = started["deliberation_id"]
        self.assertEqual(started["status"], "QUEUED")

        # poll status via the harness /api (which proxies to the real /mcp)
        result = None
        deadline = time.time() + 8
        while time.time() < deadline:
            with urllib.request.urlopen(self.base + "/api/status?id=" + did, timeout=5) as r:
                result = json.loads(r.read())
            if result["status"] == "COMPLETED":
                break
            time.sleep(0.05)
        self.assertEqual(result["status"], "COMPLETED")
        self.assertIsNotNone(result["synthesis"])
        self.assertEqual(len(result["perspectives"]), 4)


if __name__ == "__main__":
    unittest.main()
