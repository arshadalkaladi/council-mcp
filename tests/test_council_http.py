"""Council over the full MCP/HTTP stack with the worker running:
start_deliberation -> (worker) -> get_deliberation completed, plus cancel and
cross-account isolation."""

import json
import os
import tempfile
import threading
import time
import unittest
import urllib.request

from council_mcp.config import Config
from council_mcp.http_app import make_server
from council_mcp.auth.tokens import TokenIssuer

SECRET = b"council-http-secret"
ISSUER = "http://council.test"
AUD = "council-mcp"


class CouncilHttpTest(unittest.TestCase):
    def setUp(self):
        db_path = os.path.join(tempfile.mkdtemp(), "t.db")
        cfg = Config(host="127.0.0.1", port=0, issuer=ISSUER, audience=AUD, db_path=db_path)
        self.server = make_server(cfg, SECRET, host="127.0.0.1", port=0)
        self.app = self.server._app
        self.port = self.server.server_address[1]
        self.base = f"http://127.0.0.1:{self.port}"
        self.issuer = TokenIssuer(SECRET, issuer=ISSUER, audience=AUD)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.app.start()  # start the worker pool

    def tearDown(self):
        self.app.stop()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def _mcp(self, body, token, session_id=None):
        headers = {"Authorization": f"Bearer {token}",
                   "Content-Type": "application/json",
                   "Accept": "application/json, text/event-stream"}
        if session_id:
            headers["Mcp-Session-Id"] = session_id
        req = urllib.request.Request(self.base + "/mcp",
                                     data=json.dumps(body).encode(),
                                     headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, dict(resp.headers), json.loads(resp.read())

    def _session(self, token):
        _, headers, _ = self._mcp(
            {"jsonrpc": "2.0", "id": 1, "method": "initialize"}, token)
        return headers["Mcp-Session-Id"]

    def _call(self, token, sid, name, args):
        _, _, body = self._mcp({
            "jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {"name": name, "arguments": args},
        }, token, sid)
        return json.loads(body["result"]["content"][0]["text"])

    def test_council_tools_listed(self):
        token = self.issuer.issue("acct-A")
        sid = self._session(token)
        _, _, body = self._mcp(
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, token, sid)
        names = {t["name"] for t in body["result"]["tools"]}
        self.assertIn("start_deliberation", names)
        self.assertIn("get_deliberation", names)
        self.assertIn("cancel_deliberation", names)

    def test_start_then_get_completed(self):
        token = self.issuer.issue("acct-A")
        sid = self._session(token)
        started = self._call(token, sid, "start_deliberation",
                             {"question": "Should I move or stay?"})
        did = started["deliberation_id"]
        self.assertEqual(started["status"], "QUEUED")

        # Poll get_deliberation until COMPLETED (worker runs in background).
        deadline = time.time() + 8
        result = None
        while time.time() < deadline:
            result = self._call(token, sid, "get_deliberation", {"deliberation_id": did})
            if result["status"] == "COMPLETED":
                break
            time.sleep(0.05)
        self.assertEqual(result["status"], "COMPLETED")
        self.assertIsNotNone(result["synthesis"])
        self.assertEqual(len(result["perspectives"]), 4)

    def test_cross_account_get_is_not_found(self):
        token_a = self.issuer.issue("acct-A")
        sid_a = self._session(token_a)
        started = self._call(token_a, sid_a, "start_deliberation", {"question": "q"})
        did = started["deliberation_id"]

        token_b = self.issuer.issue("acct-B")
        sid_b = self._session(token_b)
        result = self._call(token_b, sid_b, "get_deliberation", {"deliberation_id": did})
        self.assertEqual(result.get("error"), "not_found")


if __name__ == "__main__":
    unittest.main()
