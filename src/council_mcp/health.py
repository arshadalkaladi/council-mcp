"""Minimal, dependency-free health endpoint for the Phase-1A skeleton.

This is intentionally built on the standard library only. The real MCP
Streamable-HTTP transport arrives in Phase 1C; this module exists so the
skeleton is runnable and testable from the first phase, and so deployment
targets have a liveness probe.

Routes:
    GET /healthz  -> 200 {"status": "ok", "service": ..., "version": ...}
    (anything else) -> 404 {"error": "not_found"}

The health endpoint is unauthenticated by design and returns no account state.
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import __version__

SERVICE_NAME = "council-mcp"


class _HealthHandler(BaseHTTPRequestHandler):
    server_version = f"{SERVICE_NAME}/{__version__}"

    def _write_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 (stdlib naming)
        if self.path == "/healthz":
            self._write_json(200, {
                "status": "ok",
                "service": SERVICE_NAME,
                "version": __version__,
            })
        else:
            self._write_json(404, {"error": "not_found"})

    def log_message(self, fmt: str, *args) -> None:
        # Quiet by default. Later phases route through a redaction-aware logger;
        # the skeleton must never dump request lines (which could carry tokens)
        # to stderr.
        return


def make_server(host: str = "127.0.0.1", port: int = 8080) -> ThreadingHTTPServer:
    """Build (but do not start) a health HTTP server. Pass port=0 for ephemeral."""
    return ThreadingHTTPServer((host, port), _HealthHandler)


def main() -> None:
    from .config import Config

    cfg = Config.from_env()
    server = make_server(cfg.host, cfg.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
