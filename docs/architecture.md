# council-mcp — Frozen Architecture & Build Plan

This document freezes the verified architecture and owner decisions that govern
implementation. It is self-contained; it references no other project.

## Verified constraints (Phase 0 / 0B)

1. Transport: **Streamable HTTP** (MCP spec 2025-11-25; HTTP+SSE deprecated).
2. Auth: **OAuth 2.1 Authorization Code Grant + PKCE S256**; token on every request.
3. Persistence identity: derived from **our** authorization server's validated
   linked account. No assumed Amazon customer id.
4. MCP tool round-trip must stay under the verified Alexa+ latency requirement
   (**< 500 ms**).
5. Long work must **not** run synchronously in a tool call. Use the
   application-level async pattern: `start_x(...)` → return a handle fast →
   background work → `get_x(handle)` → return status/result fast.
6. Do **not** depend on MCP-native Tasks (optional future capability only).
7. Do not assume Alexa+ auto-polls, waits silently, proactively pushes results,
   or supplies session/conversation ids. Design for **next-turn retrieval**.
8. All durable state belongs to our server (SQLite). Clean-room; no external
   application imports; no personal data.

## Owner decisions

1. **Concept:** A — Deliberation Council (Concept B not built).
2. **Runtime:** Python (asyncio; official MCP SDK; stdlib `sqlite3`; pytest).
3. **Repo:** `council-mcp`, Apache-2.0, standalone directory.
4. **Reasoning:** deterministic demo provider by default; optional external
   provider behind the same interface, OFF by default (local Ollama target).
5. **Cadence:** right-sized phase-gated ritual — scope → implement → test →
   prove → PRINT commit commands → STOP for review → approve → execute →
   verify. Self-contained seals/tags at milestone boundaries only (they chain
   nothing external). Conventional-commit messages. Progress notes live in the
   developer's own tooling, not in this repo.
6. **Build boundary:** local build through Phase 2C is authorized. GitHub repo
   creation, first push, and all Alexa/Amazon onboarding + deploy are each
   separately gated.

## System boundary

```
Alexa+ (MCP client)
  → OAuth 2.1 + PKCE S256 (auth boundary)
  → Streamable HTTP (MCP boundary)
  → council service (application boundary; no long work inline)
  → durable SQLite store + bounded background worker
  → ReasoningProvider (deterministic default | optional external)
```

## Concept A state machines

Deliberation: `QUEUED → RUNNING → SYNTHESIZING → COMPLETED`, with `FAILED`
from RUNNING/SYNTHESIZING and `CANCELLED` from any non-terminal state.
Job: `QUEUED → CLAIMED → RUNNING → SUCCEEDED | FAILED (retry→QUEUED / DEAD)`;
stale CLAIMED/RUNNING recovered to QUEUED on restart.

## Build phases (STOP for owner review after each)

- **1A** Skeleton: repo, config, `/healthz`, import guard. *(this phase)*
- **1B** Auth/security: OAuth 2.1 + PKCE, PRM, 401, bearer→account, redaction.
- **1C** MCP transport: Streamable HTTP, capabilities, dispatch, schema validation.
- **1D** Persistence: SQLite store, migrations, account-scoped queries, restart.
- **1E** Background jobs: bounded worker, claim/retry/recovery/shutdown.
- **2A** Council core: perspectives, orchestration, synthesis, dissent, audit.
- **2B** Deterministic demo provider + demo scripts.
- **2C** Full test matrix + local-harness proof. *(local build boundary)*
- **3**  Alexa integration (separately gated).
- **4**  Certification (separately gated).
- **5**  Submission package (separately gated).
