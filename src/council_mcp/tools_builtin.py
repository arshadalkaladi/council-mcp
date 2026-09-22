"""Built-in tool registration.

Phase 1C ships a single diagnostic `echo` tool to prove the tools/list +
tools/call + schema-validation path end to end. The council tools
(start_deliberation / get_deliberation / cancel_deliberation) will be registered
here in Phase 2A, reusing the same registry and validation.
"""

from __future__ import annotations

from .mcp.registry import ToolRegistry, text_result

_ECHO_SCHEMA = {
    "type": "object",
    "properties": {"message": {"type": "string"}},
    "required": ["message"],
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
