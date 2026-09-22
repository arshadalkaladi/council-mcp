# council-mcp — Deliberation Council for Alexa+

A standalone [Model Context Protocol](https://modelcontextprotocol.io) server that
lets Alexa+ convene a **council of perspectives** on a hard question, deliberate
**asynchronously** in the background, and return a **synthesis with preserved
dissent and a full audit trail**.

This is a clean-room, self-contained project with no dependency on any other
codebase and no personal data.

## Status

**Phase 1A — standalone skeleton.** Standard-library only; runnable and testable
with nothing but Python 3.11+. The MCP Streamable-HTTP transport, OAuth 2.1
authentication, persistence, and the council engine arrive in later phases per
the frozen build plan in [`docs/architecture.md`](docs/architecture.md).

## Quick start (Phase 1A)

Run the health endpoint (no dependencies required):

```bash
PYTHONPATH=src python -m council_mcp.health
# GET http://127.0.0.1:8080/healthz  ->  {"status":"ok",...}
```

Run the test suite (standard library `unittest`):

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

Run the clean-room import guard:

```bash
python tools/import_guard.py        # exits 0 when the tree is clean
```

## Architecture

The design is frozen in [`docs/architecture.md`](docs/architecture.md): Alexa+ →
OAuth 2.1 (PKCE S256) → Streamable HTTP → MCP server → council service →
durable store + bounded background worker → pluggable reasoning provider
(deterministic by default). Every MCP tool returns quickly; long deliberation
runs off-request and is retrieved on a later turn.

## License

[Apache-2.0](LICENSE). See [`NOTICE`](NOTICE).
