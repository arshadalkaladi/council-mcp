"""Composed HTTP app (standard library only).

Routes:
  GET  /healthz                                  -> 200 liveness (unauthenticated)
  GET  /.well-known/oauth-authorization-server   -> 200 AS metadata (RFC 8414)
  GET  /.well-known/oauth-protected-resource     -> 200 PRM (RFC 9728)
  GET  /whoami                                   -> 200 {account_id} (PROTECTED)
  POST /mcp                                      -> MCP Streamable-HTTP endpoint
                                                    (PROTECTED; JSON-RPC 2.0)

Protected routes require a valid Bearer token; failures return 401 +
WWW-Authenticate. When no signing secret is configured, protected routes fail
closed with 503.
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .auth import gate, metadata
from .auth.errors import AuthError
from .auth.tokens import TokenIssuer
from .config import Config, token_secret_from_env
from .health import health_payload
from .mcp.registry import ToolRegistry
from .mcp.server import MCPServer, RequestContext
from .tools_builtin import register_builtin_tools

_MAX_BODY_BYTES = 256 * 1024  # cap request bodies (oversize protection)
_SESSION_HEADER = "Mcp-Session-Id"


class App:
    def __init__(self, config: Config, issuer: TokenIssuer | None):
        self.config = config
        self.issuer = issuer
        self.base_url = config.base_url()
        self.registry = ToolRegistry()
        register_builtin_tools(self.registry)
        self.mcp = MCPServer(self.registry)


def _make_handler(app: App):
    class _Handler(BaseHTTPRequestHandler):
        server_version = "council-mcp"

        # -- response helpers --------------------------------------------
        def _write_json(self, status: int, payload: dict, extra_headers=None):
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            for k, v in (extra_headers or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def _write_no_content(self, status: int):
            self.send_response(status)
            self.send_header("Content-Length", "0")
            self.end_headers()

        # -- auth --------------------------------------------------------
        def _authenticate(self):
            """Return account_id, or None after writing a 401/503 response."""
            if app.issuer is None:
                self._write_json(503, {"error": "auth_unavailable"})
                return None
            try:
                result = gate.authenticate(self.headers.get("Authorization"), app.issuer)
            except AuthError as exc:
                self._write_json(
                    401,
                    {"error": exc.oauth_error, "error_description": exc.message},
                    {"WWW-Authenticate": gate.build_challenge(app.base_url, exc)},
                )
                return None
            return result.account_id

        # -- GET ---------------------------------------------------------
        def do_GET(self):  # noqa: N802
            if self.path == "/healthz":
                self._write_json(200, health_payload())
            elif self.path == metadata.AS_METADATA_PATH:
                self._write_json(200, metadata.authorization_server_metadata(app.base_url))
            elif self.path == metadata.PRM_PATH:
                self._write_json(
                    200, metadata.protected_resource_metadata(app.base_url, app.config.audience)
                )
            elif self.path == "/whoami":
                account_id = self._authenticate()
                if account_id is not None:
                    self._write_json(200, {"account_id": account_id})
            else:
                self._write_json(404, {"error": "not_found"})

        # -- POST (MCP) --------------------------------------------------
        def do_POST(self):  # noqa: N802
            if self.path != "/mcp":
                self._write_json(404, {"error": "not_found"})
                return

            account_id = self._authenticate()
            if account_id is None:
                return

            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                self._write_json(400, {"error": "invalid_content_length"})
                return
            if length <= 0 or length > _MAX_BODY_BYTES:
                self._write_json(400, {"error": "invalid_or_oversized_body"})
                return

            raw = self.rfile.read(length)
            try:
                message = json.loads(raw)
            except (ValueError, json.JSONDecodeError):
                self._write_json(400, {"error": "invalid_json"})
                return

            ctx = RequestContext(
                account_id=account_id,
                session_id=self.headers.get(_SESSION_HEADER),
            )
            outcome = app.mcp.handle(message, ctx)
            extra = {_SESSION_HEADER: outcome.session_id} if outcome.session_id else None
            if outcome.body is None:
                self._write_no_content(outcome.status)
            else:
                self._write_json(outcome.status, outcome.body, extra)

        def log_message(self, fmt, *args):
            return  # never dump request lines (may carry Authorization)

    return _Handler


def build_app(config: Config | None = None, secret: bytes | None = None) -> App:
    cfg = config or Config.from_env()
    sec = secret if secret is not None else token_secret_from_env()
    issuer = (
        TokenIssuer(sec, issuer=cfg.base_url(), audience=cfg.audience) if sec else None
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
