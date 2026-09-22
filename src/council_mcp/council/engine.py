"""The deliberation engine: orchestration + state machine (restart-safe).

run_deliberation is the background job handler (kind="deliberation"). It drives:

    QUEUED -> RUNNING -> SYNTHESIZING -> COMPLETED

with FAILED on unexpected error and cooperative CANCELLED handling. Each state
transition uses an optimistic guard (expected_status), so if a cancel arrives
between phases the next guarded transition fails and the engine stops cleanly.

Restart-safe / idempotent: if a crash requeues the job while the deliberation is
mid-flight, the engine resumes from the current state — it skips perspectives
already computed and re-synthesizes idempotently (synthesis uses INSERT OR
REPLACE). A single perspective failure is contained (recorded, partial=True) and
does not abort the deliberation.
"""

from __future__ import annotations

from .perspectives import PERSPECTIVES, evaluate
from .synthesis import synthesize

_TERMINAL = ("COMPLETED", "CANCELLED", "FAILED")


def run_deliberation(job: dict, store, provider) -> None:
    account_id = job["account_id"]
    deliberation_id = job["ref_id"]

    try:
        delib = store.get_deliberation(account_id, deliberation_id)
        if delib is None or delib["status"] in _TERMINAL:
            return

        # QUEUED -> RUNNING (guarded; stops if cancelled meanwhile).
        if delib["status"] == "QUEUED":
            if not store.update_deliberation_status(
                account_id, deliberation_id, "RUNNING", expected_status="QUEUED"
            ):
                return
            store.append_audit(account_id, deliberation_id, "running", "perspectives starting")

        question = delib["question"]
        # Perspectives already computed successfully (idempotent resume).
        done = {
            p["perspective"]
            for p in store.list_perspective_results(account_id, deliberation_id)
            if not p["failed"]
        }

        for name, description in PERSPECTIVES:
            current = store.get_deliberation(account_id, deliberation_id)
            if current is None or current["status"] in _TERMINAL:
                return  # cancelled/failed elsewhere
            if name in done:
                continue
            try:
                result = evaluate(question, name, description, provider)
                store.save_perspective_result(
                    account_id, deliberation_id, name,
                    stance=result.stance, argument=result.argument,
                    confidence=result.confidence, evidence=result.evidence, failed=False,
                )
                store.append_audit(account_id, deliberation_id, "perspective", name)
            except Exception as exc:  # noqa: BLE001 - contain per-perspective failure
                store.save_perspective_result(
                    account_id, deliberation_id, name, failed=True,
                    error=type(exc).__name__,
                )
                store.append_audit(account_id, deliberation_id, "perspective_failed", name)

        # RUNNING -> SYNTHESIZING (guarded; skip if already resuming there).
        current = store.get_deliberation(account_id, deliberation_id)
        if current is None or current["status"] in _TERMINAL:
            return
        if current["status"] == "RUNNING":
            if not store.update_deliberation_status(
                account_id, deliberation_id, "SYNTHESIZING", expected_status="RUNNING"
            ):
                return
            store.append_audit(account_id, deliberation_id, "synthesizing", None)

        results = store.list_perspective_results(account_id, deliberation_id)
        synth = synthesize(results)
        store.save_synthesis(
            account_id, deliberation_id,
            recommendation=synth["recommendation"], rationale=synth["rationale"],
            confidence=synth["confidence"], considered=synth["considered"],
            dissents=synth["dissents"],
        )
        partial = any(r["failed"] for r in results)

        # SYNTHESIZING -> COMPLETED (guarded).
        if not store.update_deliberation_status(
            account_id, deliberation_id, "COMPLETED",
            expected_status="SYNTHESIZING", partial=partial, terminal=True,
        ):
            return
        store.append_audit(account_id, deliberation_id, "completed", "synthesis ready")

    except Exception:
        # Unexpected error: best-effort FAILED (only if still non-terminal),
        # then re-raise so the worker also records the job failure.
        store.fail_deliberation(account_id, deliberation_id)
        store.append_audit(account_id, deliberation_id, "failed", "unexpected error")
        raise
