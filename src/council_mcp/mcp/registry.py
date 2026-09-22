"""Tool registry: declaration, listing, and validated invocation.

A tool handler has the signature:
    handler(arguments: dict, ctx) -> dict     # a CallToolResult body

`ctx` carries the authenticated account_id so handlers can scope state to the
caller (used from Phase 2A onward). The registry validates arguments against the
tool's closed input schema before calling the handler. Handler exceptions become
an error CallToolResult (isError=True), never a leaked stack trace.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from . import schema
from .jsonrpc import INVALID_PARAMS, METHOD_NOT_FOUND, JsonRpcError

ToolHandler = Callable[[dict, object], dict]


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    input_schema: dict
    handler: ToolHandler


def text_result(text: str, is_error: bool = False) -> dict:
    """Build a CallToolResult body with a single text content block."""
    return {"content": [{"type": "text", "text": text}], "isError": is_error}


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, name: str, description: str, input_schema: dict,
                 handler: ToolHandler) -> None:
        if name in self._tools:
            raise ValueError(f"tool already registered: {name}")
        self._tools[name] = Tool(name, description, input_schema, handler)

    def list_tools(self) -> list[dict]:
        return [
            {"name": t.name, "description": t.description, "inputSchema": t.input_schema}
            for t in self._tools.values()
        ]

    def call(self, name: str, arguments: dict, ctx: object) -> dict:
        tool = self._tools.get(name)
        if tool is None:
            raise JsonRpcError(METHOD_NOT_FOUND, f"unknown tool: {name}")

        cleaned, errors = schema.validate_and_coerce(tool.input_schema, arguments or {})
        if errors:
            raise JsonRpcError(INVALID_PARAMS, "invalid tool arguments",
                               data={"errors": errors})

        try:
            return tool.handler(cleaned, ctx)
        except JsonRpcError:
            raise
        except Exception as exc:  # noqa: BLE001 - contain handler failures
            # Never surface internals; return a safe error result.
            return text_result(f"tool '{name}' failed: {type(exc).__name__}",
                               is_error=True)
