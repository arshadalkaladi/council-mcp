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

# Substrings that mark a value as secret-like. Used by redact() so we never
# emit tokens/keys/passwords into logs even by accident.
_SECRETISH = ("token", "secret", "password", "passwd", "api_key", "apikey",
              "authorization", "bearer", "client_secret", "private")


@dataclass(frozen=True)
class Config:
    """Immutable, environment-derived runtime settings."""

    host: str = "127.0.0.1"
    port: int = 8080
    env: str = "development"

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
        return cls(
            host=e.get(ENV_HOST, "127.0.0.1"),
            port=port,
            env=e.get(ENV_ENV, "development"),
        )


def redact(key: str, value: str) -> str:
    """Return a log-safe rendering of a config/header pair.

    Any key whose name looks secret-like is masked. This is the single
    chokepoint later phases reuse before logging anything.
    """
    if any(marker in key.lower() for marker in _SECRETISH):
        return "***REDACTED***"
    return value
