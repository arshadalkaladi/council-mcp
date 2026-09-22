# council-mcp — Deliberation Council for Alexa+

> Ask a hard question. A council of four independent perspectives deliberates in
> the background, then returns a **synthesis with the dissent preserved** and a
> full audit trail — delivered to Alexa+ over the **Model Context Protocol**.

`council-mcp` is a standalone, self-hosted **MCP server** (spec **2025-11-25**,
Streamable HTTP) that gives Alexa+ a "second opinion" faculty: instead of one
answer, the customer gets a reasoned recommendation *and* the minority views that
argue against it. It runs fully offline with a deterministic reasoning provider
(zero cost, reproducible) and can optionally use a local Ollama model.

Built for the Amazon **Build, Ship, Shape** Developer Hackathon (Alexa+ track,
self-hosted MCP server). Clean-room, Apache-2.0, Python 3.11+, **no third-party
runtime dependencies**.

---

## Architecture at a glance

```
Customer ──▶ Alexa+ (MCP client) ──Streamable HTTP + OAuth2.1 Bearer──▶ council-mcp
                                                                          │
   /mcp (JSON-RPC 2.0)         /.well-known/oauth-*      /healthz         │
        │                                                                 │
        ▼                                                                 │
   MCP transport ─▶ bearer gate (OAuth 2.1 + PKCE S256, account-scoped)   │
        │                                                                 │
        ▼                                                                 │
   CouncilService ──start_deliberation()──▶ SQLite (WAL) + job queue      │
        │                                        │                        │
        │                                        ▼                        │
        │                              bounded background worker          │
        │                                        │                        │
        │              ┌─────────────────────────┼───────────────────┐   │
        │              ▼            ▼             ▼            ▼           │
        │          practical      risk        evidence   counterargument  │  (4 independent
        │              └─────────────┬───────────────────┘               │   perspectives)
        │                            ▼                                     │
        │                    synthesis (+ preserved dissent)              │
        ▼                            │                                     │
   get_deliberation() ◀──────────────┘  status · synthesis · dissent · audit
```

**Why this shape (verified against Alexa+ docs):**
- Alexa+ requires MCP **Streamable HTTP** and a **< 500 ms** tool round-trip, so a
  real deliberation can't run inside one tool call. `start_deliberation` returns a
  handle fast; the council runs in a **background worker**; `get_deliberation`
  fetches the result on a later turn (the documented "return stable identifiers"
  pattern).
- Security follows the Alexa+ account-linking contract: **OAuth 2.1 Authorization
  Code + PKCE S256**, `401 + WWW-Authenticate`, Protected Resource Metadata.
- **One** reasoning engine, **one** store, **one** worker — the web UI and tests
  all drive the same certified path.

## Quick start

Everything below runs with **just Python 3.11+** — no installs, no accounts, no
network (the default reasoning provider is offline).

```bash
# 1) Certify the whole system (import guard + full test suite + deterministic demo)
bash tools/certify.sh

# 2) See a full council deliberation over the real MCP/HTTP interface
PYTHONPATH=src python demo/deterministic_demo.py

# 3) Prove standard MCP-client compatibility (Inspector-equivalent handshake)
PYTHONPATH=src python tools/mcp_client_probe.py

# 4) Alexa+-style web simulation — then open http://127.0.0.1:8800
PYTHONPATH=src python demo/web_sim.py

# 5) Run the server yourself
export COUNCIL_MCP_TOKEN_SECRET=dev-secret     # required for protected routes
PYTHONPATH=src python -m council_mcp.http_app  # /healthz /.well-known/* /mcp
```

Optional local model (falls back to deterministic on any error):

```bash
ollama pull qwen3:8b
PYTHONPATH=src OLLAMA_MODEL=qwen3:8b python demo/ollama_demo.py
```

## MCP tools

| Tool | Purpose |
|---|---|
| `start_deliberation(question)` | Begin a deliberation; returns `{deliberation_id, status}` fast (< 500 ms) |
| `get_deliberation(deliberation_id)` | Status; when done: synthesis, dissent, per-perspective stances, audit trail |
| `cancel_deliberation(deliberation_id)` | Cooperatively cancel an in-progress deliberation |

Capabilities advertised: **`tools` only** (MCP-native `tasks` intentionally not
advertised — long work uses the application-level start/get pattern).

## Security & isolation

- OAuth 2.1 + PKCE **S256**; unauthenticated requests get `401` + `WWW-Authenticate`
  pointing at the Protected Resource Metadata.
- Every request resolves to an `account_id`; **every** store read/write is
  account-scoped — one account cannot see or touch another's deliberations.
- MCP sessions are **bound to the authenticated account** (a foreign session → 404).
- The token signing secret lives only in the environment — never in the repo, logs,
  or responses.

## Reasoning providers

- **DeterministicDemoProvider** (default): offline, zero-cost, byte-for-byte
  reproducible — the certified/demo path.
- **OllamaProvider** (optional, OFF by default): local model via HTTP; bounded
  timeout + response-size caps; question treated as untrusted data; **any failure
  falls back to deterministic** so a deliberation always completes.

## Testing

`bash tools/certify.sh` runs the clean-room import guard, the full stdlib
`unittest` suite, and the deterministic demo. The suite covers auth, MCP contract,
persistence + restart, background workers/retry/recovery, council flow,
cancellation, cross-account isolation, provider fallback, and the demo/web-sim.

## Project layout

```
src/council_mcp/   auth/ · mcp/ · store/ · jobs/ · council/ · http_app.py · config.py
tests/             full unittest suite
tools/             import_guard.py · certify.sh · mcp_client_probe.py · build_local_seal.py
demo/              deterministic_demo.py · ollama_demo.py · web_sim.py · RUNBOOK.md · STORYBOARD.md
docs/              architecture.md · DEVPOST.md · AMAZON_FEEDBACK.md
```

## License

[Apache-2.0](LICENSE). See [`NOTICE`](NOTICE).
