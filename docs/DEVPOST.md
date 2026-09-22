# Devpost project draft — council-mcp (Deliberation Council for Alexa+)

> Draft only. Not submitted. Publish at submission time (repo made public then).

## Elevator pitch (≤ 200 chars)
Alexa+ usually gives one answer. council-mcp gives a **council** — four
perspectives deliberate over MCP and return a recommendation *with the dissent
preserved*. Offline, secure, self-hosted.

## Inspiration
Good decisions weigh trade-offs, but assistants tend to collapse everything into a
single confident reply. We wanted Alexa+ to be able to say *"here's my
recommendation — and here's who disagreed and why."* The Model Context Protocol
made it possible to add that faculty to Alexa+ without touching Alexa itself.

## What it does
Ask a hard question. council-mcp convenes four independent perspectives —
**practical, risk, evidence, counterargument** — deliberates in the background,
and returns a **synthesis** (recommendation + confidence + rationale) that
**preserves dissent** (which perspectives disagreed and their positions), plus a
full **audit trail** of how the decision was reached.

## How we built it
- A self-hosted **MCP server** implementing spec **2025-11-25** over **Streamable
  HTTP** (`initialize`, `tools/list`, `tools/call`, account-bound sessions).
- Three MCP tools: `start_deliberation`, `get_deliberation`, `cancel_deliberation`.
- Because Alexa+ requires a **< 500 ms** tool round-trip, deliberation runs in a
  **bounded background worker**; the tool returns a handle immediately and the
  result is fetched on a later turn — the documented Alexa+ "stable identifier"
  pattern.
- Security to the Alexa+ account-linking contract: **OAuth 2.1 Authorization Code
  + PKCE S256**, `401 + WWW-Authenticate`, Protected Resource Metadata; every
  request account-scoped.
- **SQLite (WAL)** persistence with migrations and restart recovery.
- A **deterministic, offline** reasoning provider (zero cost, reproducible) with an
  **optional local Ollama** provider that safely falls back to deterministic.
- Python 3.11+, **no third-party runtime dependencies**; Apache-2.0; clean-room.

## Challenges we ran into
- Designing around the **< 500 ms** budget: solved with an async start/get pattern
  instead of MCP-native Tasks (which Alexa+ does not document as supported).
- Keeping the demo **reproducible** for judges: a deterministic provider makes
  every run identical and offline.
- Making cancellation and **restart** safe: cooperative cancellation via optimistic
  status guards, and an idempotent, resumable engine.

## Accomplishments we're proud of
- A full, **certified** local system (import-guard clean, complete test suite,
  one-command `tools/certify.sh`) with a real end-to-end MCP proof.
- **Dissent is a first-class output**, never averaged away.
- Runs with nothing but Python — great for judges and for privacy.

## What we learned
- The current Alexa+ MCP integration model in depth (transport, auth, latency,
  session/identity), and how to fit a genuinely async faculty into it.

## What's next
- Connect to Alexa+ directly once the Alexa+ Developer Console / MCP Toolkit opens
  for self-serve (currently "Coming Soon" / select-partners).
- An Add-on Agent Skill, richer perspectives, and per-user memory.

## How to run
See the repo README + `demo/RUNBOOK.md`. TL;DR: `bash tools/certify.sh`, then
`PYTHONPATH=src python demo/web_sim.py` and open http://127.0.0.1:8800.

## Built with
Python, MCP (2025-11-25), Streamable HTTP, OAuth 2.1 + PKCE, SQLite, (optional) Ollama.
