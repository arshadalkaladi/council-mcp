"""HS256 bearer token issue/validate tests."""

import unittest

from council_mcp.auth.errors import (
    TokenClaimsInvalid,
    TokenExpired,
    TokenMalformed,
    TokenSignatureInvalid,
)
from council_mcp.auth.tokens import TokenIssuer

SECRET = b"test-secret-do-not-use-in-prod"
ISS = "http://127.0.0.1:8080"
AUD = "council-mcp"


def issuer(secret=SECRET, iss=ISS, aud=AUD):
    return TokenIssuer(secret, issuer=iss, audience=aud)


class TokenTest(unittest.TestCase):
    def test_roundtrip_preserves_account(self):
        i = issuer()
        tok = i.issue("acct-123", ttl_seconds=3600, now=1000)
        claims = i.validate(tok, now=1001)
        self.assertEqual(claims.account_id, "acct-123")
        self.assertEqual(claims.issuer, ISS)
        self.assertEqual(claims.audience, AUD)
        self.assertEqual(claims.expires_at, 4600)

    def test_expired_rejected(self):
        i = issuer()
        tok = i.issue("acct-123", ttl_seconds=10, now=1000)
        with self.assertRaises(TokenExpired):
            i.validate(tok, now=1010)  # exp == now -> expired

    def test_bad_signature_rejected(self):
        good = issuer()
        forged = issuer(secret=b"different-secret")
        tok = forged.issue("acct-123", now=1000)
        with self.assertRaises(TokenSignatureInvalid):
            good.validate(tok, now=1001)

    def test_tampered_payload_rejected(self):
        i = issuer()
        tok = i.issue("acct-123", now=1000)
        h, p, s = tok.split(".")
        # Swap payload for another account's payload but keep old signature.
        other = i.issue("acct-999", now=1000)
        _, p2, _ = other.split(".")
        tampered = f"{h}.{p2}.{s}"
        with self.assertRaises(TokenSignatureInvalid):
            i.validate(tampered, now=1001)

    def test_issuer_mismatch_rejected(self):
        i = issuer()
        tok = i.issue("acct-123", now=1000)
        other = issuer(iss="http://evil")
        with self.assertRaises(TokenClaimsInvalid):
            other.validate(tok, now=1001)

    def test_audience_mismatch_rejected(self):
        i = issuer()
        tok = i.issue("acct-123", now=1000)
        other = issuer(aud="someone-else")
        with self.assertRaises(TokenClaimsInvalid):
            other.validate(tok, now=1001)

    def test_malformed_rejected(self):
        i = issuer()
        with self.assertRaises(TokenMalformed):
            i.validate("not-a-token", now=1000)
        with self.assertRaises(TokenMalformed):
            i.validate("", now=1000)

    def test_empty_secret_rejected(self):
        with self.assertRaises(ValueError):
            TokenIssuer(b"", issuer=ISS, audience=AUD)


if __name__ == "__main__":
    unittest.main()
