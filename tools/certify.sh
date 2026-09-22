#!/usr/bin/env bash
# Canonical local certification for council-mcp:
#   1) clean-room import guard
#   2) full test suite (stdlib unittest)
#   3) deterministic council demo end-to-end over MCP/HTTP
# Exits non-zero if any step fails.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "== [1/3] clean-room import guard =="
python3 tools/import_guard.py src tools demo

echo
echo "== [2/3] full test suite =="
PYTHONPATH=src python3 -m unittest discover -s tests

echo
echo "== [3/3] deterministic council demo (offline, over MCP/HTTP) =="
PYTHONPATH=src python3 demo/deterministic_demo.py

echo
echo "== CERTIFICATION PASSED =="
