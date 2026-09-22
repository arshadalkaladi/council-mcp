#!/usr/bin/env python3
"""Alexa+-style web simulation for council-mcp (local demo harness).

This is a DEMO HARNESS, not part of the shipped package and not a second
reasoning engine. It boots the real, certified council server in-process and
serves a small web UI. Every deliberation flows through the real MCP tools
(start_deliberation / get_deliberation) over the real /mcp endpoint:

    browser  ->  /api/*  (this harness, server-side, holds the bearer token)
             ->  /mcp    (the certified council server: OAuth-gated, MCP 2025-11-25)
             ->  council engine (4 perspectives -> synthesis -> dissent -> audit)

The token stays server-side; the browser only calls same-origin /api/*.

Run:
    PYTHONPATH=src python demo/web_sim.py         # then open http://127.0.0.1:8800
"""

import json
import os
import sys
import tempfile
import threading
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from council_mcp.config import Config           # noqa: E402
from council_mcp.http_app import make_server     # noqa: E402
from council_mcp.auth.tokens import TokenIssuer   # noqa: E402

SECRET = b"web-sim-secret-not-for-production"
ISSUER = "http://council.sim"
AUD = "council-mcp"

PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Deliberation Council — Alexa+ simulation</title>
<style>
 :root{color-scheme:dark}
 body{margin:0;font:16px system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:#0b1020;color:#e8ecf5}
 .wrap{max-width:760px;margin:0 auto;padding:24px 16px}
 h1{font-size:20px;font-weight:650;letter-spacing:.2px}
 .sub{color:#8b96b0;font-size:13px;margin-top:-8px}
 .bar{display:flex;gap:8px;margin:18px 0}
 input{flex:1;padding:14px 16px;border-radius:14px;border:1px solid #2a3350;background:#121a30;color:#e8ecf5;font-size:15px}
 button{padding:14px 18px;border:0;border-radius:14px;background:#3b82f6;color:#fff;font-weight:600;cursor:pointer}
 button:disabled{opacity:.5;cursor:default}
 .card{background:#121a30;border:1px solid #2a3350;border-radius:18px;padding:18px;margin:14px 0}
 .status{font-size:13px;color:#8b96b0}
 .rec{font-size:22px;font-weight:700;margin:6px 0}
 .pill{display:inline-block;padding:3px 10px;border-radius:999px;font-size:12px;margin-right:6px}
 .support{background:#0f3d2e;color:#5ee6a8}.oppose{background:#3d1420;color:#ff8fa3}
 .conditional{background:#3a3410;color:#ffe07a}.inconclusive{background:#2a3350;color:#9fb0d0}
 .p{border-top:1px solid #222c47;padding:10px 0}
 .pn{font-weight:600}.arg{color:#c3cbe0;font-size:14px;margin-top:4px}
 .dis{color:#ffb0bd;font-size:13px;margin-top:8px}
 .audit{color:#6f7ba0;font-size:12px;margin-top:10px;font-family:ui-monospace,monospace}
 .foot{color:#6f7ba0;font-size:12px;margin-top:22px}
</style></head>
<body><div class="wrap">
 <h1>🗣️ Deliberation Council <span class="status">· Alexa+ simulation</span></h1>
 <p class="sub">Ask a hard question. A council of four independent perspectives deliberates, then returns a synthesis with dissent preserved — over real MCP.</p>
 <div class="bar">
   <input id="q" placeholder="Should a small team enter the Alexa+ hackathon?" />
   <button id="go">Deliberate</button>
 </div>
 <div id="out"></div>
 <p class="foot">All reasoning runs through the certified council-mcp server (MCP 2025-11-25, OAuth-gated). This page never sees the token.</p>
</div>
<script>
const out=document.getElementById('out'), q=document.getElementById('q'), go=document.getElementById('go');
function esc(s){return (s||'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));}
function render(r){
  if(!r){out.innerHTML='';return;}
  let h='<div class="card"><div class="status">status: '+esc(r.status)+(r.partial?' · partial':'')+'</div>';
  if(r.synthesis){
    const rec=esc(r.synthesis.recommendation);
    h+='<div class="rec"><span class="pill '+rec+'">'+rec+'</span> confidence '+r.synthesis.confidence+'</div>';
    h+='<div class="arg">'+esc(r.synthesis.rationale)+'</div>';
  } else { h+='<div class="arg">deliberating…</div>'; }
  (r.perspectives||[]).forEach(p=>{
    h+='<div class="p"><span class="pn">'+esc(p.perspective)+'</span> · <span class="pill '+esc(p.stance)+'">'+esc(p.stance)+'</span> · '+ (p.confidence??'')+'</div>';
  });
  if(r.dissents&&r.dissents.length){h+='<div class="dis">⚖ dissent: '+r.dissents.map(d=>esc(d.perspective)+' ('+esc(d.position)+')').join(', ')+'</div>';}
  if(r.audit){h+='<div class="audit">'+r.audit.map(e=>esc(e.type)).join(' → ')+'</div>';}
  h+='</div>'; out.innerHTML=h;
}
async function run(){
  go.disabled=true; render({status:'QUEUED',perspectives:[]});
  const question=q.value||q.placeholder;
  const s=await (await fetch('/api/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question})})).json();
  const id=s.deliberation_id;
  for(let i=0;i<300;i++){
    const r=await (await fetch('/api/status?id='+encodeURIComponent(id))).json();
    render(r);
    if(['COMPLETED','FAILED','CANCELLED'].includes(r.status))break;
    await new Promise(z=>setTimeout(z,250));
  }
  go.disabled=false;
}
go.onclick=run; q.addEventListener('keydown',e=>{if(e.key==='Enter')run();});
</script></body></html>"""


class WebSim:
    def __init__(self, sim_port: int = 8800):
        self.sim_port = sim_port
        db = os.path.join(tempfile.mkdtemp(), "web_sim.db")
        cfg = Config(host="127.0.0.1", port=0, issuer=ISSUER, audience=AUD, db_path=db)
        self.app_server = make_server(cfg, SECRET, host="127.0.0.1", port=0)
        self.app = self.app_server._app  # type: ignore[attr-defined]
        self.app_base = f"http://127.0.0.1:{self.app_server.server_address[1]}"
        self.token = TokenIssuer(SECRET, issuer=cfg.base_url(), audience=cfg.audience).issue("sim-owner")
        self.sid = None
        self._app_thread = None
        self.sim_server = None
        self._sim_thread = None

    def _mcp(self, body):
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json",
                   "Accept": "application/json, text/event-stream"}
        if self.sid:
            headers["Mcp-Session-Id"] = self.sid
        req = urllib.request.Request(self.app_base + "/mcp", data=json.dumps(body).encode(),
                                     headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return dict(resp.headers), json.loads(resp.read())

    def _tool(self, name, args):
        _, body = self._mcp({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                             "params": {"name": name, "arguments": args}})
        return json.loads(body["result"]["content"][0]["text"])

    def start(self):
        self._app_thread = threading.Thread(target=self.app_server.serve_forever, daemon=True)
        self._app_thread.start()
        self.app.start()
        hd, _ = self._mcp({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
        self.sid = hd["Mcp-Session-Id"]
        self.sim_server = ThreadingHTTPServer(("127.0.0.1", self.sim_port), _make_sim_handler(self))
        self.sim_port = self.sim_server.server_address[1]
        self._sim_thread = threading.Thread(target=self.sim_server.serve_forever, daemon=True)
        self._sim_thread.start()
        return self

    def stop(self):
        if self.sim_server:
            self.sim_server.shutdown()
            self.sim_server.server_close()
        self.app.stop()
        self.app_server.shutdown()
        self.app_server.server_close()

    # convenience for tests
    def start_deliberation(self, question):
        return self._tool("start_deliberation", {"question": question})

    def get_deliberation(self, did):
        return self._tool("get_deliberation", {"deliberation_id": did})


def _make_sim_handler(sim: WebSim):
    class _H(BaseHTTPRequestHandler):
        def _json(self, code, payload):
            b = json.dumps(payload).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def do_GET(self):
            if self.path == "/" or self.path.startswith("/index"):
                b = PAGE.encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(b)))
                self.end_headers()
                self.wfile.write(b)
            elif self.path.startswith("/api/status"):
                qs = urllib.parse.urlparse(self.path).query
                did = urllib.parse.parse_qs(qs).get("id", [""])[0]
                try:
                    self._json(200, sim.get_deliberation(did))
                except Exception:
                    self._json(502, {"error": "upstream"})
            else:
                self._json(404, {"error": "not_found"})

        def do_POST(self):
            if self.path == "/api/start":
                length = int(self.headers.get("Content-Length", "0"))
                body = json.loads(self.rfile.read(length) or b"{}")
                question = (body.get("question") or "").strip() or "Should a small team enter the Alexa+ hackathon?"
                self._json(200, sim.start_deliberation(question))
            else:
                self._json(404, {"error": "not_found"})

        def log_message(self, *a):
            return

    return _H


def main():
    sim = WebSim(sim_port=int(os.environ.get("SIM_PORT", "8800"))).start()
    print(f"council-mcp web simulation running at http://127.0.0.1:{sim.sim_port}")
    print("(certified council server is proxied server-side; Ctrl+C to stop)")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        sim.stop()


if __name__ == "__main__":
    main()
