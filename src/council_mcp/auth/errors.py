"""Typed authentication errors.

Each carries an OAuth-style `error` code used in the WWW-Authenticate challenge.
Messages are safe to surface; they never include the token or the secret.
"""

from __future__ import annotations


class AuthError(Exception):
    """Base class for authentication failures. HTTP status is always 401."""

    oauth_error = "invalid_token"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class TokenMissing(AuthError):
    oauth_error = "invalid_request"


class TokenMalformed(AuthError):
    oauth_error = "invalid_token"


class TokenSignatureInvalid(AuthError):
    oauth_error = "invalid_token"


class TokenExpired(AuthError):
    oauth_error = "invalid_token"


class TokenClaimsInvalid(AuthError):
    """Issuer/audience mismatch or missing required claim."""

    oauth_error = "invalid_token"
