"""MCP protocol handler tests, including cross-account session isolation."""

import unittest

from council_mcp.mcp.jsonrpc import METHOD_NOT_FOUND
from council_mcp.mcp.registry import ToolRegistry, text_result
from council_mcp.mcp.server import MCPServer, RequestContext


def build_server():
    reg = ToolRegistry()
    reg.register("echo", "echo", {
        "type": "object",
        "properties": {"message": {"type": "string"}},
        "required": ["message"],
        "additionalProperties": False,
    }, lambda args, ctx: text_result(args["message"]))
    return MCPServer(reg)


def initialize(server, account_id="acct-A"):
    ctx = RequestContext(account_id=account_id)
    out = server.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize"}, ctx)
    return out


class MCPServerTest(unittest.TestCase):
    def setUp(self):
        self.server = build_server()

    def test_initialize_returns_capabilities_and_session(self):
        out = initialize(self.server)
        self.assertEqual(out.status, 200)
        self.assertIsNotNone(out.session_id)
        result = out.body["result"]
        self.assertEqual(result["protocolVersion"], "2025-11-25")
        self.assertIn("tools", result["capabilities"])
        # tasks capability must NOT be advertised
        self.assertNotIn("tasks", result["capabilities"])
        self.assertEqual(result["serverInfo"]["name"], "council-mcp")

    def test_initialized_notification_is_202(self):
        out = self.server.handle(
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            RequestContext(account_id="acct-A"),
        )
        self.assertEqual(out.status, 202)
        self.assertIsNone(out.body)

    def test_tools_list_requires_session(self):
        out = self.server.handle(
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            RequestContext(account_id="acct-A", session_id=None),
        )
        self.assertEqual(out.status, 404)

    def test_tools_list_and_call_with_session(self):
        sid = initialize(self.server).session_id
        ctx = RequestContext(account_id="acct-A", session_id=sid)
        lst = self.server.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, ctx)
        self.assertEqual(lst.body["result"]["tools"][0]["name"], "echo")
        call = self.server.handle({
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {"name": "echo", "arguments": {"message": "hey"}},
        }, ctx)
        self.assertEqual(call.body["result"]["content"][0]["text"], "hey")

    def test_ping(self):
        sid = initialize(self.server).session_id
        out = self.server.handle(
            {"jsonrpc": "2.0", "id": 9, "method": "ping"},
            RequestContext(account_id="acct-A", session_id=sid),
        )
        self.assertEqual(out.body["result"], {})

    def test_cross_account_session_rejected(self):
        # Account A initializes and gets a session.
        sid = initialize(self.server, "acct-A").session_id
        # Account B tries to reuse A's session id.
        out = self.server.handle(
            {"jsonrpc": "2.0", "id": 5, "method": "tools/list"},
            RequestContext(account_id="acct-B", session_id=sid),
        )
        self.assertEqual(out.status, 404)  # foreign session -> re-initialize

    def test_unknown_method(self):
        sid = initialize(self.server).session_id
        out = self.server.handle(
            {"jsonrpc": "2.0", "id": 6, "method": "does/not/exist"},
            RequestContext(account_id="acct-A", session_id=sid),
        )
        self.assertEqual(out.body["error"]["code"], METHOD_NOT_FOUND)

    def test_invalid_envelope(self):
        out = self.server.handle(
            {"id": 7, "method": "ping"},  # missing jsonrpc
            RequestContext(account_id="acct-A"),
        )
        self.assertIn("error", out.body)


if __name__ == "__main__":
    unittest.main()
