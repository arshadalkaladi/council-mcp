"""CouncilService — the request-path API behind the MCP tools.

Each method opens a short-lived, account-scoped store connection (safe to call
from multiple HTTP threads). start() is fast: it persists a QUEUED deliberation
and enqueues one background job, then returns a handle. get() reads current
status + synthesis + dissent + audit. cancel() requests cancellation.
"""

from __future__ import annotations

import secrets

from ..store import open_store


class CouncilService:
    def __init__(self, db_path: str, *, id_factory=None, migrate: bool = False):
        self.db_path = db_path
        self._migrate = migrate
        self._id = id_factory or (lambda: secrets.token_urlsafe(12))

    def _store(self):
        return open_store(self.db_path, migrate=self._migrate)

    def start(self, account_id: str, question: str) -> dict:
        store = self._store()
        try:
            deliberation_id = self._id()
            job_id = self._id()
            store.create_deliberation(account_id, deliberation_id, question, status="QUEUED")
            store.append_audit(account_id, deliberation_id, "created", "queued")
            store.create_job(account_id, job_id, "deliberation", deliberation_id)
            return {"deliberation_id": deliberation_id, "status": "QUEUED"}
        finally:
            store.close()

    def get(self, account_id: str, deliberation_id: str) -> dict | None:
        store = self._store()
        try:
            delib = store.get_deliberation(account_id, deliberation_id)
            if delib is None:
                return None
            synth = store.get_synthesis(account_id, deliberation_id)
            perspectives = store.list_perspective_results(account_id, deliberation_id)
            audit = store.list_audit(account_id, deliberation_id)
            return {
                "deliberation_id": deliberation_id,
                "status": delib["status"],
                "partial": bool(delib["partial"]),
                "question": delib["question"],
                "synthesis": None if synth is None else {
                    "recommendation": synth["recommendation"],
                    "rationale": synth["rationale"],
                    "confidence": synth["confidence"],
                    "considered": synth["considered"],
                },
                "dissents": [] if synth is None else synth["dissents"],
                "perspectives": [
                    {"perspective": p["perspective"], "stance": p["stance"],
                     "confidence": p["confidence"], "failed": p["failed"]}
                    for p in perspectives
                ],
                "audit": [{"type": e["type"], "detail": e["detail"]} for e in audit],
            }
        finally:
            store.close()

    def cancel(self, account_id: str, deliberation_id: str) -> dict:
        store = self._store()
        try:
            ok = store.cancel_deliberation(account_id, deliberation_id)
            if ok:
                store.append_audit(account_id, deliberation_id, "cancelled", "by owner")
                return {"deliberation_id": deliberation_id, "status": "CANCELLED"}
            return {"deliberation_id": deliberation_id, "error": "not_cancellable"}
        finally:
            store.close()
