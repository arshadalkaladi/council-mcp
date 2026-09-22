"""Bearer gate unit tests: extraction, authentication, and 401 challenge."""

import unittest

from council_mcp.auth import gate
from council_mcp.auth.errors import TokenMissing, TokenSignatureInvalid
from council_mcp.auth.tokens import TokenIssuer

SECRET = b"gate-secret"
ISS = "http://127.0.0.1:8080"
AUD = "council-mcp"


def issuer():
    return TokenIssuer(SECRET, issuer=ISS, audience=AUD)


class GateTest(unittest.TestCase):
    def test_extract_bearer_ok(self):
        self.assertEqual(gate.extract_bearer("Bearer abc.def.ghi"), "abc.def.ghi")
        self.assertEqual(gate.extract_bearer("bearer xyz"), "xyz")  # case-insensitive

    def test_extract_bearer_missing_or_wrong_scheme(self):
        for bad in (None, "", "Basic abc", "Bearer ", "Bearer"):
            with self.assertRaises(TokenMissing):
                gate.extract_bearer(bad)

    def test_authenticate_valid(self):
        i = issuer()
        tok = i.issue("acct-42", now=1000)
        result = gate.authenticate(f"Bearer {tok}", i, now=1001)
        self.assertEqual(result.account_id, "acct-42")

    def test_authenticate_missing_raises(self):
        with self.assertRaises(TokenMissing):
            gate.authenticate(None, issuer())

    def test_authenticate_bad_signature_raises(self):
        i = issuer()
        forged = TokenIssuer(b"other", issuer=ISS, audience=AUD)
        tok = forged.issue("acct-42", now=1000)
        with self.assertRaises(TokenSignatureInvalid):
            gate.authenticate(f"Bearer {tok}", i, now=1001)

    def test_build_challenge_includes_error_and_resource_metadata(self):
        err = TokenMissing("missing Authorization header")
        challenge = gate.build_challenge(ISS, err)
        self.assertIn('error="invalid_request"', challenge)
        self.assertIn("resource_metadata=", challenge)
        self.assertIn("/.well-known/oauth-protected-resource", challenge)


if __name__ == "__main__":
    unittest.main()
