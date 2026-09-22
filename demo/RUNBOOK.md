# council-mcp — Demo Runbook

Everything here runs locally with just Python 3.11+ (no installs, no accounts,
no network for the canonical path).

## 1. Certify the whole system (canonical path)

```bash
cd council-mcp
bash tools/certify.sh
```

This runs, in order:
1. the clean-room import guard (no forbidden imports/paths),
2. the full test suite (stdlib `unittest`),
3. the deterministic council demo end-to-end over MCP/HTTP.

All three must pass for certification.

## 2. Deterministic council demo (offline, reproducible)

```bash
PYTHONPATH=src python demo/deterministic_demo.py
```

Boots the real server in-process and drives a complete deliberation through the
real MCP Streamable-HTTP interface:

```
initialize -> start_deliberation -> (background worker runs 4 perspectives)
           -> get_deliberation -> synthesis + preserved dissent + audit trail
```

Output is identical on every run (deterministic provider). This is the
≤3-minute judge path — it needs nothing but Python.

## 3. Optional: local Ollama demo (NOT required for certification)

Requires a local [Ollama](https://ollama.com) with a generative model:

```bash
ollama pull qwen3:8b
PYTHONPATH=src OLLAMA_MODEL=qwen3:8b python demo/ollama_demo.py
```

Runs the same council pipeline using the local model. If Ollama is unavailable
or the model output doesn't honor the JSON contract, each perspective falls back
to the deterministic provider and the deliberation still completes.

## 4. Run the server yourself

```bash
export COUNCIL_MCP_TOKEN_SECRET=dev-secret     # required for protected routes
PYTHONPATH=src python -m council_mcp.http_app
# GET /healthz
# GET /.well-known/oauth-authorization-server   (advertises PKCE S256)
# GET /.well-known/oauth-protected-resource
# POST /mcp                                       (JSON-RPC; requires Bearer token)
```

## Notes

- The default reasoning provider is deterministic, offline, and zero-cost.
- All durable state is a local SQLite file (WAL); temp DBs are used by demos/tests.
- Every request is account-scoped; sessions are bound to the authenticated account.
