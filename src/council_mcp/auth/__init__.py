"""Authentication & security foundation for council-mcp (Phase 1B).

Standard-library only. Provides:
  * pkce   — PKCE S256 generation/verification (RFC 7636)
  * tokens — self-issued HS256 bearer tokens (issue/validate)
  * metadata — OAuth 2.1 AS metadata (RFC 8414) + Protected Resource
    Metadata (RFC 9728), advertising S256
  * gate   — bearer extraction, validation, and 401 challenge construction
  * errors — typed auth failures

The persistence key used by later phases is the validated token's subject
(`account_id`), resolved by our own token validation — never an assumed
Amazon-supplied identifier.
"""
