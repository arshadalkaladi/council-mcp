"""OAuth discovery metadata tests (RFC 8414 / RFC 9728)."""

import unittest

from council_mcp.auth import metadata


class MetadataTest(unittest.TestCase):
    def test_as_metadata_advertises_s256(self):
        md = metadata.authorization_server_metadata("http://127.0.0.1:8080/")
        self.assertEqual(md["code_challenge_methods_supported"], ["S256"])
        self.assertEqual(md["issuer"], "http://127.0.0.1:8080")
        self.assertTrue(md["authorization_endpoint"].endswith(metadata.AUTHORIZE_PATH))
        self.assertTrue(md["token_endpoint"].endswith(metadata.TOKEN_PATH))
        self.assertIn("authorization_code", md["grant_types_supported"])
        self.assertEqual(md["response_types_supported"], ["code"])

    def test_prm_points_at_authorization_server(self):
        md = metadata.protected_resource_metadata("http://host:9/", "council-mcp")
        self.assertEqual(md["resource"], "council-mcp")
        self.assertEqual(md["authorization_servers"], ["http://host:9"])
        self.assertEqual(md["bearer_methods_supported"], ["header"])

    def test_prm_url(self):
        self.assertEqual(
            metadata.prm_url("http://host:9/"),
            "http://host:9/.well-known/oauth-protected-resource",
        )


if __name__ == "__main__":
    unittest.main()
