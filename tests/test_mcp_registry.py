"""Tool registry tests."""

import unittest

from council_mcp.mcp.jsonrpc import INVALID_PARAMS, METHOD_NOT_FOUND, JsonRpcError
from council_mcp.mcp.registry import ToolRegistry, text_result

SCHEMA = {
    "type": "object",
    "properties": {"message": {"type": "string"}},
    "required": ["message"],
    "additionalProperties": False,
}


class RegistryTest(unittest.TestCase):
    def setUp(self):
        self.reg = ToolRegistry()
        self.reg.register("echo", "echo it", SCHEMA,
                          lambda args, ctx: text_result(args["message"]))

    def test_list(self):
        tools = self.reg.list_tools()
        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0]["name"], "echo")
        self.assertIn("inputSchema", tools[0])

    def test_call_ok(self):
        result = self.reg.call("echo", {"message": "hi"}, ctx=None)
        self.assertFalse(result["isError"])
        self.assertEqual(result["content"][0]["text"], "hi")

    def test_unknown_tool(self):
        with self.assertRaises(JsonRpcError) as cm:
            self.reg.call("nope", {}, ctx=None)
        self.assertEqual(cm.exception.code, METHOD_NOT_FOUND)

    def test_invalid_arguments(self):
        with self.assertRaises(JsonRpcError) as cm:
            self.reg.call("echo", {}, ctx=None)  # missing required
        self.assertEqual(cm.exception.code, INVALID_PARAMS)

    def test_duplicate_registration_rejected(self):
        with self.assertRaises(ValueError):
            self.reg.register("echo", "again", SCHEMA, lambda a, c: text_result("x"))

    def test_handler_exception_becomes_error_result(self):
        def boom(args, ctx):
            raise RuntimeError("secret-internal-detail")
        self.reg.register("boom", "boom", {"type": "object", "properties": {}}, boom)
        result = self.reg.call("boom", {}, ctx=None)
        self.assertTrue(result["isError"])
        self.assertNotIn("secret-internal-detail", result["content"][0]["text"])


if __name__ == "__main__":
    unittest.main()
