"""Runtime configuration for council-mcp.

Config comes from environment variables only. Secrets (when later phases add
them) live in the environment and are NEVER written to logs or responses. This
module deliberately has no third-party dependencies so the Phase-1A skeleton
runs on a bare Python install.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

# Environment variable names are centralized here so nothing hard-codes them.
ENV_HOST = "COUNCIL_MCP_HOST"
ENV_PORT = "COUNCIL_MCP_PORT"
ENV_ENV = "COUNCIL_MCP_ENV"
ENV_ISSUER = "OAUTH_ISSUER"
ENV_AUDIENCE = "OAUTH_AUDIENCE"
ENV_TOKEN_SECRET = "COUNCIL_MCP_TOKEN_SECRET"  # signing secret; NEVER logged/stored
ENV_DB_PATH = "COUNCIL_MCP_DB"
ENV_REASONING_PROVIDER = "REASONING_PROVIDER"   # "deterministic" (default) | "ollama"
ENV_OLLAMA_URL = "OLLAMA_URL"
ENV_OLLAMA_MODEL = "OLLAMA_MODEL"

# Substrings that mark a value as secret-like. Used by redact() so we never
# emit tokens/keys/passwords into logs even by accident.
_SECRETISH = ("token", "secret", "password", "passwd", "api_key", "apikey",
              "authorization", "bearer", "client_secret", "private")


@dataclass(frozen=True)
class Config:
    """Immutable, environment-derived runtime settings.

    NOTE: the token signing secret is deliberately NOT a field here. Dataclass
    repr would echo it, which would risk leaking it into logs. Read it only via
    token_secret_from_env(), which returns bytes and is never repr'd.
    """

    host: str = "127.0.0.1"
    port: int = 8080
    env: str = "development"
    issuer: str = ""       # non-secret; empty => derived from host:port
    audience: str = "council-mcp"
    db_path: str = "council.db"
    reasoning_provider: str = "deterministic"  # default; "ollama" to opt in
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"

    @classmethod
    def from_env(cls, environ: dict | None = None) -> "Config":
        e = os.environ if environ is None else environ
        raw_port = e.get(ENV_PORT, "8080")
        try:
            port = int(raw_port)
        except (TypeError, ValueError):
            raise ValueError(f"{ENV_PORT} must be an integer, got {raw_port!r}")
        if not (0 <= port <= 65535):
            raise ValueError(f"{ENV_PORT} out of range: {port}")
        host = e.get(ENV_HOST, "127.0.0.1")
        return cls(
            host=host,
            port=port,
            env=e.get(ENV_ENV, "development"),
            issuer=e.get(ENV_ISSUER, ""),
            audience=e.get(ENV_AUDIENCE, "council-mcp"),
            db_path=e.get(ENV_DB_PATH, "council.db"),
            reasoning_provider=e.get(ENV_REASONING_PROVIDER, "deterministic"),
            ollama_url=e.get(ENV_OLLAMA_URL, "http://localhost:11434"),
            ollama_model=e.get(ENV_OLLAMA_MODEL, "llama3"),
        )

    def base_url(self) -> str:
        """The externally-visible base URL used to build metadata/issuer."""
        return self.issuer or f"http://{self.host}:{self.port}"


def token_secret_from_env(environ: dict | None = None) -> bytes | None:
    """Return the signing secret as bytes, or None if unset.

    Kept out of Config so it is never captured in a dataclass repr or log line.
    """
    e = os.environ if environ is None else environ
    raw = e.get(ENV_TOKEN_SECRET)
    return raw.encode("utf-8") if raw else None


def redact(key: str, value: str) -> str:
    """Return a log-safe rendering of a config/header pair.

    Any key whose name looks secret-like is masked. This is the single
    chokepoint later phases reuse before logging anything.
    """
    if any(marker in key.lower() for marker in _SECRETISH):
        return "***REDACTED***"
    return value
