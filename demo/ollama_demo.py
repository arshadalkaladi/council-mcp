#!/usr/bin/env python3
"""Optional council-mcp demo using a LOCAL Ollama model.

This is NOT required for certification. It shows the optional reasoning provider
running through the exact same council pipeline. If Ollama is not running, or the
model does not honor the JSON contract, each perspective safely falls back to the
deterministic provider and the deliberation still completes.

Run (requires a local Ollama with a generative model, e.g. `ollama pull qwen3:8b`):
    PYTHONPATH=src OLLAMA_MODEL=qwen3:8b python demo/ollama_demo.py
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from council_mcp.config import Config           # noqa: E402
from deterministic_demo import run_demo, ISSUER, AUD  # noqa: E402


def main():
    model = os.environ.get("OLLAMA_MODEL", "qwen3:8b")
    url = os.environ.get("OLLAMA_URL", "http://localhost:11434")
    print(f"[optional] Using local Ollama model={model} url={url} "
          f"(falls back to deterministic on any error)\n")
    cfg = Config(host="127.0.0.1", port=0, issuer=ISSUER, audience=AUD,
                 reasoning_provider="ollama", ollama_model=model, ollama_url=url,
                 db_path=os.path.join(tempfile.mkdtemp(), "ollama_demo.db"))
    run_demo(config=cfg)


if __name__ == "__main__":
    main()
