#!/usr/bin/env python3
"""Build the self-contained local certification seal for council-mcp.

This seal is entirely self-contained: it hashes only this project's own files
and records the current git HEAD. It chains NOTHING from any external project.
Run after the feature commit so head_sha anchors the certified content:

    python3 tools/build_local_seal.py

Writes council_mcp_local_certification.json (deterministic; sorted keys).
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEAL_PATH = os.path.join(ROOT, "council_mcp_local_certification.json")

INCLUDE_DIRS = ["src", "tests", "tools", "demo", "docs"]
ROOT_FILES = ["README.md", "LICENSE", "NOTICE", "pyproject.toml", ".env.example", ".gitignore"]
INCLUDE_EXTS = {".py", ".md", ".sh", ".toml"}
EXCLUDE_PARTS = {"__pycache__", ".git"}

CLOSURE_STATUS = (
    "council-mcp LOCAL CERTIFICATION (Phase 1A-2C). A standalone, clean-room "
    "Alexa+ MCP Deliberation Council: OAuth 2.1 resource+authorization server "
    "with PKCE S256, MCP Streamable-HTTP transport, SQLite (WAL) persistence with "
    "migrations, bounded background worker with retry/recovery, the Concept A "
    "council (four independent perspectives, synthesis with preserved dissent, a "
    "QUEUED->RUNNING->SYNTHESIZING->COMPLETED state machine with FAILED and "
    "cooperative CANCELLED), a deterministic offline default provider and an "
    "optional local Ollama provider with safe fallback, strict account isolation "
    "at the store layer, and an append-only audit trail. Certified locally only: "
    "no GitHub repository, no push, no Amazon/Alexa resources, no public deploy, "
    "no OAuth registration with Alexa, no competition entry. This seal is "
    "self-contained and chains no external seal."
)


def _sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _sha_text(t: str) -> str:
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def _head_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", ROOT, "rev-parse", "HEAD"]
        ).decode().strip()
    except Exception:
        return "UNKNOWN"


def _collect_files() -> list[str]:
    files: list[str] = []
    for d in INCLUDE_DIRS:
        base = os.path.join(ROOT, d)
        for cur, dirs, names in os.walk(base):
            dirs[:] = [x for x in dirs if x not in EXCLUDE_PARTS]
            for n in names:
                if os.path.splitext(n)[1] in INCLUDE_EXTS:
                    files.append(os.path.relpath(os.path.join(cur, n), ROOT))
    for f in ROOT_FILES:
        if os.path.exists(os.path.join(ROOT, f)):
            files.append(f)
    return sorted(set(files))


def build() -> str:
    manifest = {}
    for rel in _collect_files():
        with open(os.path.join(ROOT, rel), "rb") as fh:
            manifest[rel] = _sha_bytes(fh.read())

    body = {
        "artifact": "council-mcp",
        "phase": "1A-2C local certification",
        "status": "SEALED (local)",
        "self_contained": True,
        "chains_external_seals": False,
        "head_sha": _head_sha(),
        "file_count": len(manifest),
        "manifest_sha256": _sha_text(json.dumps(manifest, sort_keys=True)),
        "manifest": manifest,
        "closure_status": CLOSURE_STATUS,
    }
    body["closure_id"] = _sha_text(body["closure_status"])
    seal_input = {k: v for k, v in body.items() if k not in ("seal_id",)}
    body["seal_id"] = _sha_text(json.dumps(seal_input, sort_keys=True))

    with open(SEAL_PATH, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(body, indent=2, sort_keys=True))

    print("WROTE", SEAL_PATH)
    print("  head_sha:", body["head_sha"])
    print("  file_count:", body["file_count"])
    print("  manifest_sha256:", body["manifest_sha256"])
    print("  seal_id:", body["seal_id"])
    return SEAL_PATH


if __name__ == "__main__":
    build()
