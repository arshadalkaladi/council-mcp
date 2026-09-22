"""JSON-RPC 2.0 framing helpers and standard error codes."""

from __future__ import annotations

# Standard JSON-RPC error codes.
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


class JsonRpcError(Exception):
    """A JSON-RPC-level error to be returned in the response `error` field."""

    def __init__(self, code: int, message: str, data=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data


def is_notification(message: dict) -> bool:
    """A JSON-RPC notification has no `id`."""
    return "id" not in message


def success(msg_id, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def error(msg_id, code: int, message: str, data=None) -> dict:
    err = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "id": msg_id, "error": err}


def validate_envelope(message: dict) -> None:
    """Raise JsonRpcError if the message is not a valid JSON-RPC 2.0 request."""
    if not isinstance(message, dict):
        raise JsonRpcError(INVALID_REQUEST, "message must be a JSON object")
    if message.get("jsonrpc") != "2.0":
        raise JsonRpcError(INVALID_REQUEST, "jsonrpc must be '2.0'")
    if "method" not in message or not isinstance(message["method"], str):
        raise JsonRpcError(INVALID_REQUEST, "missing/invalid method")
