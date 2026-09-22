"""MCP protocol handler (pure logic; HTTP glue lives in http_app).

Handles the request/response subset over parsed JSON-RPC messages:
  initialize, notifications/initialized, ping, tools/list, tools/call.

Session management: `initialize` mints an Mcp-Session-Id bound to the
authenticated account_id. Every subsequent method requires that session id AND
that it belongs to the same account — a session minted for account A cannot be
used with account B's token (cross-account isolation). Unknown/foreign sessions
yield HTTP 404 so the client re-initializes (per the Streamable-HTTP spec).
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass

from . import PROTOCOL_VERSION
from .. import __version__
from . import jsonrpc
from .jsonrpc import INVALID_PARAMS, METHOD_NOT_FOUND, JsonRpcError
from .registry import ToolRegistry


@dataclass(frozen=True)
class RequestContext:
    account_id: str
    session_id: str | None = None


@dataclass(frozen=True)
class HandlerOutcome:
    status: int
    body: dict | None            # None => no content (202)
    session_id: str | None = None  # set as Mcp-Session-Id response header


class MCPServer:
    def __init__(self, registry: ToolRegistry):
        self.registry = registry
        self._sessions: dict[str, str] = {}  # session_id -> account_id

    # -- session helpers -------------------------------------------------
    def session_account(self, session_id: str) -> str | None:
        return self._sessions.get(session_id)

    def _new_session(self, account_id: str) -> str:
        sid = secrets.token_urlsafe(24)
        self._sessions[sid] = account_id
        return sid

    def _require_session(self, ctx: RequestContext) -> HandlerOutcome | None:
        if not ctx.session_id or self._sessions.get(ctx.session_id) != ctx.account_id:
            return HandlerOutcome(404, {"error": "invalid_session"}, None)
        return None

    # -- dispatch --------------------------------------------------------
    def handle(self, message, ctx: RequestContext) -> HandlerOutcome:
        is_dict = isinstance(message, dict)
        msg_id = message.get("id") if is_dict else None
        notification = is_dict and "id" not in message

        try:
            jsonrpc.validate_envelope(message)
            method = message["method"]
            params = message.get("params") or {}

            if method == "initialize":
                return self._initialize(msg_id, ctx)
            if method == "notifications/initialized":
                return HandlerOutcome(202, None, None)

            # Everything else needs a valid, account-bound session.
            bad = self._require_session(ctx)
            if bad is not None:
                return bad

            if method == "ping":
                return HandlerOutcome(200, jsonrpc.success(msg_id, {}), None)
            if method == "tools/list":
                return HandlerOutcome(
                    200, jsonrpc.success(msg_id, {"tools": self.registry.list_tools()}), None
                )
            if method == "tools/call":
                name = params.get("name")
                args = params.get("arguments") or {}
                if not isinstance(name, str) or not name:
                    raise JsonRpcError(INVALID_PARAMS, "params.name (string) is required")
                result = self.registry.call(name, args, ctx)
                return HandlerOutcome(200, jsonrpc.success(msg_id, result), None)

            if notification:
                return HandlerOutcome(202, None, None)
            raise JsonRpcError(METHOD_NOT_FOUND, f"unknown method: {method}")

        except JsonRpcError as exc:
            if notification:
                return HandlerOutcome(202, None, None)
            return HandlerOutcome(200, jsonrpc.error(msg_id, exc.code, exc.message, exc.data), None)

    def _initialize(self, msg_id, ctx: RequestContext) -> HandlerOutcome:
        session_id = self._new_session(ctx.account_id)
        result = {
            "protocolVersion": PROTOCOL_VERSION,
            # tools only; the `tasks` capability is intentionally not advertised.
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "council-mcp", "version": __version__},
        }
        return HandlerOutcome(200, jsonrpc.success(msg_id, result), session_id)
