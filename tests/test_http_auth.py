"""Integration tests over the composed HTTP app: well-known + 401/200 flow."""

import json
import threading
import unittest
import urllib.error
import urllib.request

from council_mcp.config import Config
from council_mcp.http_app import make_server
from council_mcp.auth.tokens import TokenIssuer

SECRET = b"http-integration-secret"


class HttpAuthTest(unittest.TestCase):
    def setUp(self):
        # Pin a fixed issuer string so token validation is independent of the
        # ephemeral bind port (the app derives its issuer from config, not the
        # socket).
        self.config = Config(host="127.0.0.1", port=0,
                             issuer="http://council.test", audience="council-mcp")
        self.server = make_server(self.config, SECRET, host="127.0.0.1", port=0)
        self.port = self.server.server_address[1]
        self.base = f"http://127.0.0.1:{self.port}"
        self.issuer = TokenIssuer(SECRET, issuer="http://council.test",
                                  audience="council-mcp")
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def _get(self, path, headers=None):
        req = urllib.request.Request(self.base + path, headers=headers or {})
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status, dict(resp.headers), json.loads(resp.read())
        except urllib.error.HTTPError as e:
            try:
                return e.code, dict(e.headers), json.loads(e.read())
            finally:
                e.close()

    def test_healthz_still_ok(self):
        status, _, body = self._get("/healthz")
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "ok")

    def test_as_metadata_served_with_s256(self):
        status, _, body = self._get("/.well-known/oauth-authorization-server")
        self.assertEqual(status, 200)
        self.assertEqual(body["code_challenge_methods_supported"], ["S256"])

    def test_prm_served(self):
        status, _, body = self._get("/.well-known/oauth-protected-resource")
        self.assertEqual(status, 200)
        self.assertEqual(body["resource"], "council-mcp")

    def test_whoami_requires_token(self):
        status, headers, body = self._get("/whoami")
        self.assertEqual(status, 401)
        self.assertIn("WWW-Authenticate", headers)
        self.assertIn("resource_metadata=", headers["WWW-Authenticate"])
        self.assertEqual(body["error"], "invalid_request")

    def test_whoami_rejects_bad_token(self):
        status, headers, body = self._get(
            "/whoami", {"Authorization": "Bearer not.a.token"}
        )
        self.assertEqual(status, 401)
        self.assertIn("WWW-Authenticate", headers)

    def test_whoami_accepts_valid_token(self):
        tok = self.issuer.issue("acct-777")
        status, _, body = self._get("/whoami", {"Authorization": f"Bearer {tok}"})
        self.assertEqual(status, 200)
        self.assertEqual(body["account_id"], "acct-777")


class HttpAuthUnavailableTest(unittest.TestCase):
    """With no secret configured, protected routes fail closed (503)."""

    def setUp(self):
        self.server = make_server(Config(host="127.0.0.1", port=0), secret=b"",
                                  host="127.0.0.1", port=0)
        self.port = self.server.server_address[1]
        self.base = f"http://127.0.0.1:{self.port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def test_protected_fails_closed(self):
        req = urllib.request.Request(self.base + "/whoami")
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                code = resp.status
        except urllib.error.HTTPError as e:
            code = e.code
            e.close()
        self.assertEqual(code, 503)


if __name__ == "__main__":
    unittest.main()
