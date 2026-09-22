"""PKCE S256 tests, including the RFC 7636 Appendix B known vector."""

import unittest

from council_mcp.auth import pkce

# RFC 7636 Appendix B worked example.
RFC_VERIFIER = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
RFC_CHALLENGE = "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"


class PkceTest(unittest.TestCase):
    def test_known_vector(self):
        self.assertEqual(pkce.challenge_s256(RFC_VERIFIER), RFC_CHALLENGE)
        self.assertTrue(pkce.verify_s256(RFC_VERIFIER, RFC_CHALLENGE))

    def test_generate_verifier_length_and_roundtrip(self):
        v = pkce.generate_verifier()
        self.assertGreaterEqual(len(v), 43)
        self.assertLessEqual(len(v), 128)
        self.assertTrue(pkce.verify_s256(v, pkce.challenge_s256(v)))

    def test_wrong_verifier_rejected(self):
        self.assertFalse(pkce.verify_s256(RFC_VERIFIER + "x", RFC_CHALLENGE))
        self.assertFalse(pkce.verify_s256("", RFC_CHALLENGE))
        self.assertFalse(pkce.verify_s256(RFC_VERIFIER, ""))

    def test_too_short_verifier_rejected(self):
        self.assertFalse(pkce.verify_s256("short", pkce.challenge_s256("short")))


if __name__ == "__main__":
    unittest.main()
