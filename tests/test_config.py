"""Config parsing, base_url derivation, secret handling, and redaction."""

import unittest

from council_mcp import config as cfgmod
from council_mcp.config import Config


class ConfigTest(unittest.TestCase):
    def test_from_env_defaults(self):
        c = Config.from_env({})
        self.assertEqual(c.host, "127.0.0.1")
        self.assertEqual(c.port, 8080)
        self.assertEqual(c.audience, "council-mcp")

    def test_bad_port_rejected(self):
        with self.assertRaises(ValueError):
            Config.from_env({"COUNCIL_MCP_PORT": "not-a-number"})
        with self.assertRaises(ValueError):
            Config.from_env({"COUNCIL_MCP_PORT": "99999"})

    def test_base_url_derivation_and_override(self):
        self.assertEqual(Config(host="h", port=9).base_url(), "http://h:9")
        self.assertEqual(Config(issuer="https://x").base_url(), "https://x")

    def test_secret_not_in_config_repr(self):
        # The signing secret must never be a Config field (repr could leak it).
        c = Config.from_env({"COUNCIL_MCP_TOKEN_SECRET": "supersecretvalue"})
        self.assertNotIn("supersecretvalue", repr(c))

    def test_secret_read_only_via_helper(self):
        self.assertIsNone(cfgmod.token_secret_from_env({}))
        self.assertEqual(
            cfgmod.token_secret_from_env({"COUNCIL_MCP_TOKEN_SECRET": "abc"}),
            b"abc",
        )

    def test_redact_masks_secretish_keys(self):
        self.assertEqual(cfgmod.redact("Authorization", "Bearer xyz"), "***REDACTED***")
        self.assertEqual(cfgmod.redact("api_key", "k"), "***REDACTED***")
        self.assertEqual(cfgmod.redact("host", "127.0.0.1"), "127.0.0.1")


if __name__ == "__main__":
    unittest.main()
