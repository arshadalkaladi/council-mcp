"""MCP Streamable-HTTP transport (Phase 1C), standard-library only.

Implements the request/response subset of the MCP 2025-11-25 spec needed by
council-mcp:
  * jsonrpc  — JSON-RPC 2.0 framing + error codes
  * schema   — minimal closed-schema input validation/coercion
  * registry — tool registry (list + validated call)
  * server   — MCP protocol handler (initialize/tools.*/ping/notifications)
    with account-bound session management

The transport advertises `tools` only. It deliberately does NOT advertise the
`tasks` capability: long work uses the application-level start/get pattern, not
MCP-native tasks (frozen constraint).

A production deployment MAY replace this with the official `mcp` SDK behind the
same registry/server seam; the SDK is not required for this subset.
"""

PROTOCOL_VERSION = "2025-11-25"
