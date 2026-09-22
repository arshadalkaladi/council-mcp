"""Phase-1A acceptance: the health endpoint responds correctly.

Run with the src/ layout on the path, e.g.:
    PYTHONPATH=src python -m unittest discover -s tests
"""

import json
import threading
import unittest
import urllib.request
import urllib.error

from council_mcp.health import make_server
from council_mcp import __version__


class HealthEndpointTest(unittest.TestCase):
    def setUp(self):
        self.server = make_server("127.0.0.1", 0)  # ephemeral port
        self.host, self.port = self.server.server_address
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def _get(self, path):
        url = f"http://127.0.0.1:{self.port}{path}"
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            try:
                return e.code, json.loads(e.read().decode("utf-8"))
            finally:
                e.close()

    def test_healthz_returns_ok(self):
        status, body = self._get("/healthz")
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["service"], "council-mcp")
        self.assertEqual(body["version"], __version__)

    def test_unknown_path_returns_404(self):
        status, body = self._get("/nope")
        self.assertEqual(status, 404)
        self.assertEqual(body["error"], "not_found")


if __name__ == "__main__":
    unittest.main()
