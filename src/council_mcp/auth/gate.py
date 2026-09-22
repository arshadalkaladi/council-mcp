"""Bearer auth gate: extract, validate, and build 401 challenges.

The gate is the single chokepoint every protected route uses. On success it
returns an AuthResult carrying the account_id (the persistence key). On failure
it raises an AuthError; callers turn that into a 401 with a WWW-Authenticate
header built by build_challenge() (RFC 9728 resource_metadata pointer).
"""

from __future__ import annotations

from dataclasses import dataclass

from .errors import AuthError, TokenMissing
from .metadata import prm_url
from .tokens import Claims, TokenIssuer

_BEARER_PREFIX = "bearer "


@dataclass(frozen=True)
class AuthResult:
    account_id: str
    claims: Claims


def extract_bearer(authorization_value: str | None) -> str:
    """Pull the token out of an Authorization header value, or raise."""
    if not authorization_value:
        raise TokenMissing("missing Authorization header")
    value = authorization_value.strip()
    if not value.lower().startswith(_BEARER_PREFIX):
        raise TokenMissing("Authorization header must use the Bearer scheme")
    token = value[len(_BEARER_PREFIX):].strip()
    if not token:
        raise TokenMissing("empty bearer token")
    return token


def authenticate(authorization_value: str | None, issuer: TokenIssuer,
                 *, now: int | None = None) -> AuthResult:
    """Validate the request's bearer token and resolve the account_id."""
    token = extract_bearer(authorization_value)
    claims = issuer.validate(token, now=now)
    return AuthResult(account_id=claims.account_id, claims=claims)


def build_challenge(base_url: str, error: AuthError) -> str:
    """Construct the WWW-Authenticate header value for a 401 response."""
    # Escape any stray quotes in the human-readable description.
    desc = error.message.replace('"', "'")
    return (
        f'Bearer error="{error.oauth_error}", '
        f'error_description="{desc}", '
        f'resource_metadata="{prm_url(base_url)}"'
    )
