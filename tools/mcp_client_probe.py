#!/usr/bin/env python3
"""Generic MCP client compatibility probe (Inspector-equivalent).

Proves council-mcp speaks the MCP 2025-11-25 wire protocol to ANY standard
client: the client side here uses ONLY urllib + JSON-RPC (it imports nothing
from council_mcp), so a successful handshake demonstrates protocol conformance,
not reliance on our own code. By default it boots the server in-process so the
proof is self-contained; pass --url/--token to probe a running server instead.

Run:
    PYTHONPATH=src python tools/mcp_client_probe.py

To use the official MCP Inspector instead (needs Node):
    npx @modelcontextprotocol/inspector    # then connect to the /mcp URL with a Bearer token
"""

import argparse
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request

# --- generic MCP client (stdlib only; no council_mcp import) ---------------

def rpc(base, token, body, sid=None):
    headers = {"Content-Type": "application/json",
               "Accept": "application/json, text/event-stream"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if sid:
        headers["Mcp-Session-Id"] = sid
    req = urllib.request.Request(base + "/mcp", data=json.dumps(body).encode(),
                                 headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=10) as resp:
        raw = resp.read()
        return dict(resp.headers), (json.loads(raw) if raw else None)


def probe(base, token):
    ok = True
    print("→ initialize")
    hd, body = rpc(base, token, {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                                 "params": {"protocolVersion": "2025-11-25",
                                            "clientInfo": {"name": "probe", "version": "1"}}})
    sid = hd.get("Mcp-Session-Id")
    pv = body["result"]["protocolVersion"]
    caps = body["result"]["capabilities"]
    print(f"  protocolVersion={pv}  session={'yes' if sid else 'no'}  capabilities={list(caps)}")
    ok &= (pv == "2025-11-25") and ("tools" in caps) and ("tasks" not in caps) and bool(sid)

    print("→ notifications/initialized")
    rpc(base, token, {"jsonrpc": "2.0", "method": "notifications/initialized"}, sid)

    print("→ tools/list")
    _, body = rpc(base, token, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, sid)
    names = [t["name"] for t in body["result"]["tools"]]
    print("  tools:", names)
    ok &= {"start_deliberation", "get_deliberation", "cancel_deliberation"} <= set(names)

    print("→ tools/call start_deliberation")
    _, body = rpc(base, token, {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                                "params": {"name": "start_deliberation",
                                           "arguments": {"question": "probe question"}}}, sid)
    started = json.loads(body["result"]["content"][0]["text"])
    did = started["deliberation_id"]
    print("  deliberation_id:", did, "status:", started["status"])

    print("→ tools/call get_deliberation (poll)")
    status = None
    for _ in range(300):
        _, body = rpc(base, token, {"jsonrpc": "2.0", "id": 4, "method": "tools/call",
                                    "params": {"name": "get_deliberation",
                                               "arguments": {"deliberation_id": did}}}, sid)
        res = json.loads(body["result"]["content"][0]["text"])
        status = res["status"]
        if status in ("COMPLETED", "FAILED", "CANCELLED"):
            break
        time.sleep(0.05)
    print("  final status:", status, "| recommendation:",
          (res.get("synthesis") or {}).get("recommendation"))
    ok &= (status == "COMPLETED")

    print("→ negative: tools/call without session should be rejected (404)")
    try:
        rpc(base, token, {"jsonrpc": "2.0", "id": 5, "method": "tools/list"})
        print("  UNEXPECTED: accepted without session")
        ok = False
    except urllib.error.HTTPError as e:
        print("  rejected with HTTP", e.code)
        ok &= (e.code == 404)

    print("\nRESULT:", "PASS ✅ (standard MCP client compatible)" if ok else "FAIL ❌")
    return ok


def _boot_in_process():
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
    import tempfile
    from council_mcp.config import Config
    from council_mcp.http_app import make_server
    from council_mcp.auth.tokens import TokenIssuer
    secret = b"probe-secret"
    db = os.path.join(tempfile.mkdtemp(), "probe.db")
    cfg = Config(host="127.0.0.1", port=0, issuer="http://council.probe", audience="council-mcp", db_path=db)
    server = make_server(cfg, secret, host="127.0.0.1", port=0)
    server._app.start()  # type: ignore[attr-defined]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    token = TokenIssuer(secret, issuer=cfg.base_url(), audience=cfg.audience).issue("probe-owner")
    return server, base, token


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", help="base URL of a running server (e.g. https://host)")
    ap.add_argument("--token", help="bearer token for the running server")
    args = ap.parse_args()

    if args.url:
        ok = probe(args.url.rstrip("/"), args.token)
        raise SystemExit(0 if ok else 1)

    server, base, token = _boot_in_process()
    try:
        ok = probe(base, token)
    finally:
        server._app.stop()  # type: ignore[attr-defined]
        server.shutdown()
        server.server_close()
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
