# council-mcp — Deliberation Council for Alexa+

A standalone [Model Context Protocol](https://modelcontextprotocol.io) server that
lets Alexa+ convene a **council of perspectives** on a hard question, deliberate
**asynchronously** in the background, and return a **synthesis with preserved
dissent and a full audit trail**.

This is a clean-room, self-contained project with no dependency on any other
codebase and no personal data.

## Status

**Locally certified (Phases 1A–2C).** A complete, standalone Alexa+ MCP
Deliberation Council, runnable and testable with nothing but Python 3.11+:
OAuth 2.1 (PKCE **S256**) resource+authorization server, MCP Streamable-HTTP
transport, SQLite (WAL) persistence + migrations, a bounded background worker
with retry/recovery, the Concept A council (four independent perspectives,
synthesis with preserved dissent, full state machine), a deterministic offline
default provider and an optional local Ollama provider with safe fallback,
strict account isolation, and an audit trail. See
[`docs/architecture.md`](docs/architecture.md) and
[`demo/RUNBOOK.md`](demo/RUNBOOK.md).

Certify everything in one command:

```bash
bash tools/certify.sh   # import guard + full test suite + deterministic demo
```

## Quick start

Run the composed app (health + OAuth metadata + a demo protected route):

```bash
export COUNCIL_MCP_TOKEN_SECRET=dev-secret        # required for protected routes
PYTHONPATH=src python -m council_mcp.http_app
# GET /healthz
# GET /.well-known/oauth-authorization-server      (advertises S256)
# GET /.well-known/oauth-protected-resource
# GET /whoami                                       (401 without a valid Bearer token)
```

Run the minimal liveness-only server:

```bash
PYTHONPATH=src python -m council_mcp.health         # GET /healthz only
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
