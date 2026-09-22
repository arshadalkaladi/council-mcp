#!/usr/bin/env python3
"""Canonical council-mcp demo — fully offline, reproducible, zero-cost.

Boots the real server in-process, then drives a complete deliberation through
the real MCP Streamable-HTTP interface (initialize -> start_deliberation ->
poll get_deliberation -> synthesis with dissent + audit trail). Uses the
DeterministicDemoProvider, so it runs anywhere with just Python and is suitable
for the <=3-minute judge demonstration.

Run:
    PYTHONPATH=src python demo/deterministic_demo.py
"""

import json
import os
import sys
import tempfile
import threading
import time
import urllib.request

# Make the package importable when run directly.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from council_mcp.config import Config           # noqa: E402
from council_mcp.http_app import make_server     # noqa: E402
from council_mcp.auth.tokens import TokenIssuer   # noqa: E402

QUESTION = "Should a small team enter the Alexa+ hackathon?"
SECRET = b"demo-secret-not-for-production"
ISSUER = "http://council.demo"
AUD = "council-mcp"


def run_demo(question: str = QUESTION, quiet: bool = False, config: Config | None = None) -> dict:
    db = os.path.join(tempfile.mkdtemp(), "demo.db")
    cfg = config or Config(host="127.0.0.1", port=0, issuer=ISSUER, audience=AUD, db_path=db)
    server = make_server(cfg, SECRET, host="127.0.0.1", port=0)
    app = server._app  # type: ignore[attr-defined]
    port = server.server_address[1]
    base = f"http://127.0.0.1:{port}"
    # Mint a token whose issuer/audience match what the app validates.
    token = TokenIssuer(SECRET, issuer=cfg.base_url(), audience=cfg.audience).issue("demo-owner")

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    app.start()

    def mcp(body, sid=None):
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json",
                   "Accept": "application/json, text/event-stream"}
        if sid:
            headers["Mcp-Session-Id"] = sid
        req = urllib.request.Request(base + "/mcp", data=json.dumps(body).encode(),
                                     headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return dict(resp.headers), json.loads(resp.read())

    started = time.time()
    result = None
    try:
        hd, _ = mcp({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
        sid = hd["Mcp-Session-Id"]

        def call(name, args):
            _, body = mcp({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                           "params": {"name": name, "arguments": args}}, sid)
            return json.loads(body["result"]["content"][0]["text"])

        started_result = call("start_deliberation", {"question": question})
        did = started_result["deliberation_id"]
        for _ in range(500):
            result = call("get_deliberation", {"deliberation_id": did})
            if result["status"] in ("COMPLETED", "FAILED", "CANCELLED"):
                break
            time.sleep(0.02)
        elapsed = time.time() - started
    finally:
        app.stop()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    if not quiet:
        _render(question, result, elapsed)
    return {"result": result, "elapsed": elapsed}


def _render(question, r, elapsed):
    line = "=" * 72
    print(line)
    print("council-mcp  —  Deliberation Council demo (deterministic, offline)")
    print(line)
    print(f"Question: {question}")
    print(f"Status:   {r['status']}   partial={r['partial']}")
    print("\nPerspectives (independent):")
    for p in r["perspectives"]:
        print(f"  - {p['perspective']:<15} stance={str(p['stance']):<12} confidence={p['confidence']}")
    s = r["synthesis"]
    print("\nSynthesis:")
    print(f"  recommendation: {s['recommendation']}   confidence: {s['confidence']}")
    print(f"  rationale: {s['rationale']}")
    print(f"  dissent preserved: {r['dissents'] or 'none'}")
    print("\nAudit trail: " + " -> ".join(e["type"] for e in r["audit"]))
    print(f"\nCompleted start->result over MCP/HTTP in {elapsed:.2f}s")
    print(line)


if __name__ == "__main__":
    run_demo()
