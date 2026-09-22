"""Built-in tool registration.

Ships the diagnostic `echo` tool (kept for MCP contract checks) plus the Concept
A council tools: start_deliberation, get_deliberation, cancel_deliberation. Tool
results carry a JSON document in a text content block (universally supported by
MCP clients).
"""

from __future__ import annotations

import json

from .mcp.registry import ToolRegistry, text_result

_ECHO_SCHEMA = {
    "type": "object",
    "properties": {"message": {"type": "string"}},
    "required": ["message"],
    "additionalProperties": False,
}

_START_SCHEMA = {
    "type": "object",
    "properties": {"question": {"type": "string"}},
    "required": ["question"],
    "additionalProperties": False,
}

_ID_SCHEMA = {
    "type": "object",
    "properties": {"deliberation_id": {"type": "string"}},
    "required": ["deliberation_id"],
    "additionalProperties": False,
}


def _echo_handler(arguments: dict, ctx) -> dict:
    return text_result(arguments["message"])


def register_builtin_tools(registry: ToolRegistry) -> None:
    registry.register(
        "echo",
        "Diagnostic tool: returns the provided message unchanged.",
        _ECHO_SCHEMA,
        _echo_handler,
    )


def register_council_tools(registry: ToolRegistry, service) -> None:
    def start_handler(arguments: dict, ctx) -> dict:
        result = service.start(ctx.account_id, arguments["question"])
        return text_result(json.dumps(result))

    def get_handler(arguments: dict, ctx) -> dict:
        result = service.get(ctx.account_id, arguments["deliberation_id"])
        if result is None:
            return text_result(json.dumps({"error": "not_found"}), is_error=True)
        return text_result(json.dumps(result))

    def cancel_handler(arguments: dict, ctx) -> dict:
        result = service.cancel(ctx.account_id, arguments["deliberation_id"])
        is_error = "error" in result
        return text_result(json.dumps(result), is_error=is_error)

    registry.register(
        "start_deliberation",
        "Start a council deliberation on a question. Returns a deliberation_id; "
        "the result is retrieved later with get_deliberation.",
        _START_SCHEMA, start_handler,
    )
    registry.register(
        "get_deliberation",
        "Get a deliberation's status, and when complete its synthesis, dissent, "
        "and audit trail.",
        _ID_SCHEMA, get_handler,
    )
    registry.register(
        "cancel_deliberation",
        "Request cancellation of an in-progress deliberation.",
        _ID_SCHEMA, cancel_handler,
    )
