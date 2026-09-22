"""Composed HTTP app for Phase 1B (standard library only).

Mounts:
  GET /healthz                                  -> 200 liveness (unauthenticated)
  GET /.well-known/oauth-authorization-server   -> 200 AS metadata (RFC 8414)
  GET /.well-known/oauth-protected-resource     -> 200 PRM (RFC 9728)
  GET /whoami                                   -> 200 {account_id}  (PROTECTED)
                                                   401 + WWW-Authenticate otherwise

/whoami is a demonstration protected route proving the bearer gate + 401 flow.
The real MCP Streamable-HTTP transport (Phase 1C) reuses the same gate.

The token issuer is optional: if no signing secret is configured, protected
routes fail closed with 503 (auth unavailable) rather than silently allowing
access.
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .auth import gate, metadata
from .auth.errors import AuthError
from .auth.tokens import TokenIssuer
from .config import Config, token_secret_from_env
from .health import health_payload


class App:
    """Holds the resolved configuration + optional token issuer."""

    def __init__(self, config: Config, issuer: TokenIssuer | None):
        self.config = config
        self.issuer = issuer
        self.base_url = config.base_url()


def _make_handler(app: App):
    class _Handler(BaseHTTPRequestHandler):
        server_version = "council-mcp"

        def _write_json(self, status: int, payload: dict, extra_headers=None):
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            for k, v in (extra_headers or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def _protected(self):
            if app.issuer is None:
                self._write_json(503, {"error": "auth_unavailable"})
                return
            auth_header = self.headers.get("Authorization")
            try:
                result = gate.authenticate(auth_header, app.issuer)
            except AuthError as exc:
                challenge = gate.build_challenge(app.base_url, exc)
                self._write_json(
                    401,
                    {"error": exc.oauth_error, "error_description": exc.message},
                    {"WWW-Authenticate": challenge},
                )
                return
            self._write_json(200, {"account_id": result.account_id})

        def do_GET(self):  # noqa: N802
            if self.path == "/healthz":
                self._write_json(200, health_payload())
            elif self.path == metadata.AS_METADATA_PATH:
                self._write_json(200, metadata.authorization_server_metadata(app.base_url))
            elif self.path == metadata.PRM_PATH:
                self._write_json(
                    200,
                    metadata.protected_resource_metadata(app.base_url, app.config.audience),
                )
            elif self.path == "/whoami":
                self._protected()
            else:
                self._write_json(404, {"error": "not_found"})

        def log_message(self, fmt, *args):
            # Never dump request lines (they can carry Authorization) to stderr.
            return

    return _Handler


def build_app(config: Config | None = None, secret: bytes | None = None) -> App:
    cfg = config or Config.from_env()
    sec = secret if secret is not None else token_secret_from_env()
    issuer = (
        TokenIssuer(sec, issuer=cfg.base_url(), audience=cfg.audience)
        if sec else None
    )
    return App(cfg, issuer)


def make_server(config: Config | None = None, secret: bytes | None = None,
                *, host: str | None = None, port: int | None = None) -> ThreadingHTTPServer:
    app = build_app(config, secret)
    bind_host = host if host is not None else app.config.host
    bind_port = port if port is not None else app.config.port
    return ThreadingHTTPServer((bind_host, bind_port), _make_handler(app))


def main() -> None:
    server = make_server()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
