"""The council's independent perspectives.

Each perspective is evaluated independently via the provider; there is no shared
mutable state between them. This is a clean-room set (not copied from any other
project): practical, risk, evidence, counterargument.
"""

from __future__ import annotations

from dataclasses import dataclass

# (name, description). Order is stable so runs are reproducible.
PERSPECTIVES: list[tuple[str, str]] = [
    ("practical", "weighs feasibility, cost, and day-to-day consequences"),
    ("risk", "surfaces downside, failure modes, and what could go wrong"),
    ("evidence", "grounds the view in facts and what is actually known"),
    ("counterargument", "argues against the leading view to stress-test it"),
]


@dataclass(frozen=True)
class PerspectiveResult:
    perspective: str
    stance: str | None
    argument: str | None
    confidence: float | None
    evidence: list
    failed: bool = False
    error: str | None = None


def evaluate(question: str, perspective: str, description: str, provider) -> PerspectiveResult:
    out = provider.analyze(question, perspective, description)
    return PerspectiveResult(
        perspective=perspective,
        stance=out.stance,
        argument=out.argument,
        confidence=out.confidence,
        evidence=out.evidence,
    )
