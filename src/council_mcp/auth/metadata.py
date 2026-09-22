"""OAuth 2.1 discovery metadata.

Alexa reads these well-known documents to discover our endpoints and to confirm
PKCE S256 support (deployment is blocked without it). Two documents:

  * Authorization Server Metadata (RFC 8414):
        /.well-known/oauth-authorization-server
  * Protected Resource Metadata (RFC 9728):
        /.well-known/oauth-protected-resource

Both are pure functions of the base URL + audience, so they are trivially
testable and contain no secrets.
"""

from __future__ import annotations

AS_METADATA_PATH = "/.well-known/oauth-authorization-server"
PRM_PATH = "/.well-known/oauth-protected-resource"

AUTHORIZE_PATH = "/oauth/authorize"
TOKEN_PATH = "/oauth/token"


def authorization_server_metadata(base_url: str) -> dict:
    base = base_url.rstrip("/")
    return {
        "issuer": base,
        "authorization_endpoint": f"{base}{AUTHORIZE_PATH}",
        "token_endpoint": f"{base}{TOKEN_PATH}",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "code_challenge_methods_supported": ["S256"],
        "token_endpoint_auth_methods_supported": ["none"],
    }


def protected_resource_metadata(base_url: str, audience: str) -> dict:
    base = base_url.rstrip("/")
    return {
        "resource": audience,
        "authorization_servers": [base],
        "bearer_methods_supported": ["header"],
        "resource_documentation": f"{base}/",
    }


def prm_url(base_url: str) -> str:
    return f"{base_url.rstrip('/')}{PRM_PATH}"
