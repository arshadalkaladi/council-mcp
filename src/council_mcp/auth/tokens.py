"""Self-issued bearer tokens (HS256), standard-library only.

This is a compact JWS/JWT-style token (header.payload.signature, base64url,
HMAC-SHA256). It is the Resource-Server side of the design: our own
authorization server issues tokens bound to a linked account, and every MCP
request is validated here to resolve the account_id persistence key.

Security properties enforced on validate():
  * signature verified with hmac.compare_digest (constant time)
  * exp (expiry) checked
  * iss / aud checked when configured
  * required subject (account_id) present

A production deployment MAY swap this for a vetted JWT/OAuth library behind the
same TokenIssuer interface; the primitives here (hmac/hashlib) are the same ones
such libraries use for HS256.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass

from .errors import (
    TokenClaimsInvalid,
    TokenExpired,
    TokenMalformed,
    TokenSignatureInvalid,
)

_ALG = "HS256"
_HEADER = {"alg": _ALG, "typ": "JWT"}


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64url_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


@dataclass(frozen=True)
class Claims:
    account_id: str
    issuer: str
    audience: str
    issued_at: int
    expires_at: int


class TokenIssuer:
    """Issues and validates HS256 tokens with a fixed secret + iss/aud."""

    def __init__(self, secret: bytes, *, issuer: str, audience: str):
        if not secret:
            raise ValueError("token secret must be non-empty")
        self._secret = secret
        self.issuer = issuer
        self.audience = audience

    def _sign(self, signing_input: bytes) -> str:
        sig = hmac.new(self._secret, signing_input, hashlib.sha256).digest()
        return _b64url_encode(sig)

    def issue(self, account_id: str, *, ttl_seconds: int = 3600,
              now: int | None = None) -> str:
        if not account_id:
            raise ValueError("account_id required")
        iat = int(time.time()) if now is None else now
        payload = {
            "sub": account_id,
            "iss": self.issuer,
            "aud": self.audience,
            "iat": iat,
            "exp": iat + int(ttl_seconds),
        }
        header_b64 = _b64url_encode(json.dumps(_HEADER, separators=(",", ":")).encode())
        payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        return f"{header_b64}.{payload_b64}.{self._sign(signing_input)}"

    def validate(self, token: str, *, now: int | None = None) -> Claims:
        if not token or token.count(".") != 2:
            raise TokenMalformed("token is not a well-formed JWS")
        header_b64, payload_b64, sig_b64 = token.split(".")

        # Verify signature first (constant time), before trusting any content.
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        expected_sig = self._sign(signing_input)
        if not hmac.compare_digest(expected_sig, sig_b64):
            raise TokenSignatureInvalid("bad signature")

        try:
            header = json.loads(_b64url_decode(header_b64))
            payload = json.loads(_b64url_decode(payload_b64))
        except (ValueError, json.JSONDecodeError) as exc:
            raise TokenMalformed(f"undecodable token segment: {exc}") from exc

        if header.get("alg") != _ALG:
            raise TokenClaimsInvalid(f"unexpected alg: {header.get('alg')!r}")

        sub = payload.get("sub")
        exp = payload.get("exp")
        iat = payload.get("iat")
        if not sub or not isinstance(exp, int) or not isinstance(iat, int):
            raise TokenClaimsInvalid("missing/invalid sub/exp/iat")

        current = int(time.time()) if now is None else now
        if current >= exp:
            raise TokenExpired("token expired")

        if payload.get("iss") != self.issuer:
            raise TokenClaimsInvalid("issuer mismatch")
        if payload.get("aud") != self.audience:
            raise TokenClaimsInvalid("audience mismatch")

        return Claims(
            account_id=sub,
            issuer=payload["iss"],
            audience=payload["aud"],
            issued_at=iat,
            expires_at=exp,
        )
