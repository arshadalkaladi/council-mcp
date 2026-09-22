# council-mcp — Hackathon Submission Runbook

**Event:** Amazon "Build, Ship, Shape" Developer Hackathon — **Alexa+ track**
(self-hosted MCP server). Rules: https://amazonappdev2026.devpost.com/rules
**Deadline:** Fri **Oct 23, 2026, 12:00 pm Pacific**. Submission window opened
Aug 31, 2026 — council-mcp was created Sept 21–22, 2026 (in-window ✅).

## Qualification (verified against the rules)
- ✅ Self-hosted MCP server, spec **2025-11-25** over Streamable HTTP.
- ✅ Newly created during the submission window.
- ✅ Eligibility: UAE not excluded; not OFAC-sanctioned; entrant is of age of majority.
- ✅ Solo entry allowed.
- ✅ Original, solely-owned, clean-room work; Apache-2.0 (license detectable in GitHub "About").
- ✅ Live deployment not required — repo + <3-min video + working code (demo + web sim) suffice.

## Deliverables & where the content lives
| Deliverable | Source / status |
|---|---|
| **Code repo URL (GitHub)** | `github.com/arshadalkaladi/council-mcp` — currently **PRIVATE**; make **public** (Apache-2.0 auto-detected) OR keep private and share with `testing@devpost.com` + Amazon team |
| **Demo video (<3 min, public YouTube/Vimeo)** | Script: [`demo/STORYBOARD.md`](STORYBOARD.md) — owner records + uploads |
| **Text description** | [`docs/DEVPOST.md`](DEVPOST.md) — paste into Devpost |
| **Product feedback** | [`docs/AMAZON_FEEDBACK.md`](AMAZON_FEEDBACK.md) — maps to the 5 required questions |
| **Track** | Select **Alexa+** primary track |

## Owner submission steps (each is a consequential/outward action — do in order)
1. **Make the repo public** (or choose the private+share path). *(First outward step.)*
2. **Record the demo video** from `demo/STORYBOARD.md` (<3 min) and **upload it publicly** to YouTube or Vimeo; copy the URL.
3. **Register on Devpost** and **Join Hackathon** (free Devpost account).
4. **Create the project submission:** paste the description (`DEVPOST.md`), the feedback (`AMAZON_FEEDBACK.md`), the **repo URL**, the **video URL**; select the **Alexa+** track.
5. **Submit** before the deadline. Keep a screenshot/confirmation.

## Pre-submission local check (anytime)
```bash
bash tools/certify.sh          # guard + full test suite + deterministic demo
PYTHONPATH=src python tools/mcp_client_probe.py   # standard MCP client compatibility
PYTHONPATH=src python demo/web_sim.py             # visual Alexa+-style demo (for the video)
```

## What KAAAJ has prepared vs. what needs the owner
- **Prepared (done):** the entire codebase (certified, 138 tests), README, architecture docs, description draft, feedback draft, video storyboard, MCP compatibility proof, web simulation.
- **Needs owner (outward, gated):** repo public flip; video recording + upload; Devpost registration; final submission. KAAAJ cannot create the Devpost account, record/upload the video, or click submit — those are yours.
