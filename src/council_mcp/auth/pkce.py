"""PKCE (RFC 7636) — S256 only.

Alexa+ requires the authorization server to advertise and support S256. This
module generates verifiers/challenges and verifies a verifier against a
challenge in constant time. Standard library only.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

# RFC 7636: code_verifier is 43..128 chars of the unreserved set.
_VERIFIER_MIN = 43
_VERIFIER_MAX = 128


def _b64url_nopad(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def generate_verifier(n_bytes: int = 32) -> str:
    """Return a high-entropy code_verifier (43 chars for 32 bytes)."""
    verifier = _b64url_nopad(secrets.token_bytes(n_bytes))
    # token_bytes(32) -> 43 chars; clamp defensively.
    return verifier[:_VERIFIER_MAX]


def challenge_s256(verifier: str) -> str:
    """Compute the S256 code_challenge for a verifier."""
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return _b64url_nopad(digest)


def verify_s256(verifier: str, challenge: str) -> bool:
    """Constant-time check that `verifier` matches `challenge` under S256."""
    if not verifier or not challenge:
        return False
    if not (_VERIFIER_MIN <= len(verifier) <= _VERIFIER_MAX):
        return False
    expected = challenge_s256(verifier)
    return hmac.compare_digest(expected, challenge)
