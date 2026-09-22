"""Synthesis: compose a recommendation while PRESERVING dissent.

Deterministic aggregation over the perspective results:
  * weight each usable stance by its confidence,
  * pick the highest-weight stance (ties broken by stance name for determinism),
  * report mean confidence of contributing perspectives,
  * list every perspective that disagreed as explicit dissent.

Dissent is a first-class output, never discarded.
"""

from __future__ import annotations


def synthesize(results: list[dict]) -> dict:
    considered = [r["perspective"] for r in results]
    usable = [r for r in results if not r.get("failed") and r.get("stance")]

    if not usable:
        return {
            "recommendation": "inconclusive",
            "rationale": "No perspective produced a usable result.",
            "confidence": 0.0,
            "considered": considered,
            "dissents": [],
        }

    tally: dict[str, float] = {}
    for r in usable:
        tally[r["stance"]] = tally.get(r["stance"], 0.0) + (r["confidence"] or 0.0)
    # Highest weight wins; deterministic tie-break by stance name.
    winner = sorted(tally.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]

    confidence = round(sum((r["confidence"] or 0.0) for r in usable) / len(usable), 3)
    dissents = [
        {"perspective": r["perspective"], "position": r["stance"]}
        for r in usable if r["stance"] != winner
    ]
    if dissents:
        dissent_note = " Dissent noted from: " + ", ".join(d["perspective"] for d in dissents) + "."
    else:
        dissent_note = " No dissent among contributing perspectives."
    rationale = (
        f"{len(usable)} of {len(results)} perspectives contributed; the weighted "
        f"balance favors '{winner}'.{dissent_note}"
    )

    return {
        "recommendation": winner,
        "rationale": rationale,
        "confidence": confidence,
        "considered": considered,
        "dissents": dissents,
    }
