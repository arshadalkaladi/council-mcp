# Demo Storyboard — council-mcp (target: under 3 minutes)

Goal: convince a judge in <3 min that this is a real, secure, self-hosted MCP
server (spec 2025-11-25) that gives Alexa+ a genuinely useful new faculty —
multi-perspective deliberation with preserved dissent — and that it runs offline
and reproducibly.

Recording setup: terminal + browser side by side. Deterministic provider (so the
recording is repeatable). No secrets on screen.

---

### Scene 1 — The idea (0:00–0:25)
- On camera / voiceover: "Alexa+ usually gives you one answer. Real decisions have
  trade-offs. **council-mcp** gives Alexa+ a council — four independent
  perspectives that deliberate, then hand back a recommendation *and the dissent*."
- Show the README architecture-at-a-glance diagram.

### Scene 2 — It's a real MCP server (0:25–0:55)
- Terminal: `PYTHONPATH=src python tools/mcp_client_probe.py`
- Point at the output: `protocolVersion=2025-11-25`, `capabilities=['tools']`,
  tools listed, a full `initialize → tools/list → tools/call` handshake, and the
  "no session → 404" security check. Say: "Standard MCP client, standard wire
  protocol — Inspector-equivalent."

### Scene 3 — The Alexa+ experience (0:55–1:50)
- Browser: `PYTHONPATH=src python demo/web_sim.py` → open http://127.0.0.1:8800
- Type: *"Should a small team enter the Alexa+ hackathon?"* → Deliberate.
- Narrate the card as it fills: status QUEUED → running → the four perspectives
  appear (practical / risk / evidence / counterargument), then the **synthesis**
  with a recommendation and confidence, and the **⚖ dissent** line.
- Emphasize: "This whole thing ran through the real MCP endpoint, OAuth-gated, in
  the background — the tool call returned in milliseconds, exactly as Alexa+'s
  <500 ms budget requires."

### Scene 4 — Why it's trustworthy (1:50–2:25)
- Terminal: `bash tools/certify.sh` → show import guard clean, the test count, and
  "CERTIFICATION PASSED".
- One line each: OAuth 2.1 + PKCE S256; account-scoped isolation; SQLite
  persistence + restart recovery; deterministic + optional local Ollama with safe
  fallback; dissent is never discarded.

### Scene 5 — Close (2:25–2:55)
- "Self-hosted MCP server, spec 2025-11-25, Apache-2.0, zero-cost to run, ready
  for Alexa+ when the add-on console opens. Council-mcp: don't just get an
  answer — hear the whole room."
- Show the public GitHub URL (once the repo is made public at submission).

---

Backup shot (optional): `demo/ollama_demo.py` with a local model, to show the
optional real-model path and the safe fallback.
