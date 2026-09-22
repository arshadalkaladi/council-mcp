"""End-to-end MCP contract over HTTP: initialize -> tools/list -> tools/call,
with auth enforcement and session handling."""

import json
import threading
import unittest
import urllib.error
import urllib.request

from council_mcp.config import Config
from council_mcp.http_app import make_server
from council_mcp.auth.tokens import TokenIssuer

SECRET = b"mcp-http-secret"
ISSUER = "http://council.test"
AUD = "council-mcp"


class MCPHttpTest(unittest.TestCase):
    def setUp(self):
        cfg = Config(host="127.0.0.1", port=0, issuer=ISSUER, audience=AUD)
        self.server = make_server(cfg, SECRET, host="127.0.0.1", port=0)
        self.port = self.server.server_address[1]
        self.base = f"http://127.0.0.1:{self.port}"
        self.issuer = TokenIssuer(SECRET, issuer=ISSUER, audience=AUD)
        self.token = self.issuer.issue("acct-A")
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def _post_mcp(self, body, token=None, session_id=None):
        headers = {"Content-Type": "application/json",
                   "Accept": "application/json, text/event-stream"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if session_id:
            headers["Mcp-Session-Id"] = session_id
        req = urllib.request.Request(
            self.base + "/mcp", data=json.dumps(body).encode(),
            headers=headers, method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                raw = resp.read()
                parsed = json.loads(raw) if raw else None
                return resp.status, dict(resp.headers), parsed
        except urllib.error.HTTPError as e:
            try:
                raw = e.read()
                return e.code, dict(e.headers), (json.loads(raw) if raw else None)
            finally:
                e.close()

    def test_mcp_requires_auth(self):
        status, headers, _ = self._post_mcp(
            {"jsonrpc": "2.0", "id": 1, "method": "initialize"}, token=None
        )
        self.assertEqual(status, 401)
        self.assertIn("WWW-Authenticate", headers)

    def test_full_contract_flow(self):
        # initialize
        status, headers, body = self._post_mcp(
            {"jsonrpc": "2.0", "id": 1, "method": "initialize"}, token=self.token
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["result"]["protocolVersion"], "2025-11-25")
        sid = headers.get("Mcp-Session-Id")
        self.assertTrue(sid)

        # initialized notification -> 202
        status, _, _ = self._post_mcp(
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            token=self.token, session_id=sid,
        )
        self.assertEqual(status, 202)

        # tools/list
        status, _, body = self._post_mcp(
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            token=self.token, session_id=sid,
        )
        self.assertEqual(status, 200)
        names = [t["name"] for t in body["result"]["tools"]]
        self.assertIn("echo", names)

        # tools/call
        status, _, body = self._post_mcp(
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
             "params": {"name": "echo", "arguments": {"message": "contract-ok"}}},
            token=self.token, session_id=sid,
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["result"]["content"][0]["text"], "contract-ok")

    def test_missing_session_yields_404(self):
        status, _, _ = self._post_mcp(
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            token=self.token, session_id=None,
        )
        self.assertEqual(status, 404)

    def test_cross_account_session_isolation_over_http(self):
        # Account A initializes.
        _, headers, _ = self._post_mcp(
            {"jsonrpc": "2.0", "id": 1, "method": "initialize"}, token=self.token
        )
        sid = headers.get("Mcp-Session-Id")
        # Account B presents its own valid token but A's session id.
        token_b = self.issuer.issue("acct-B")
        status, _, _ = self._post_mcp(
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            token=token_b, session_id=sid,
        )
        self.assertEqual(status, 404)

    def test_invalid_json_yields_400(self):
        headers = {"Authorization": f"Bearer {self.token}",
                   "Content-Type": "application/json"}
        req = urllib.request.Request(self.base + "/mcp", data=b"{not json",
                                     headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                code = resp.status
        except urllib.error.HTTPError as e:
            code = e.code
            e.close()
        self.assertEqual(code, 400)


if __name__ == "__main__":
    unittest.main()
