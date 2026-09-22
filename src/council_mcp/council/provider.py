"""Reasoning provider abstraction.

The council calls a ReasoningProvider to produce each perspective's analysis.
The default DeterministicDemoProvider is fully offline and reproducible (same
input -> same output), so the entire demo and test suite run with no paid
inference and no dependency on any other system. An optional external provider
(Phase 2B) can implement the same interface behind an env flag; it is never the
default.
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class PerspectiveOutput:
    stance: str            # "support" | "oppose" | "conditional"
    argument: str
    confidence: float      # 0.0 .. 1.0
    evidence: list         # list of {claim, source_kind, note}


class ReasoningProvider(ABC):
    @abstractmethod
    def analyze(self, question: str, perspective: str, description: str) -> PerspectiveOutput:
        ...


_STANCES = ("support", "oppose", "conditional")


class DeterministicDemoProvider(ReasoningProvider):
    """Offline, reproducible provider derived from a hash of (perspective, question).

    No network, no inference, no randomness — the demo is byte-for-byte
    repeatable, which is exactly what a judge run needs.
    """

    def analyze(self, question: str, perspective: str, description: str) -> PerspectiveOutput:
        h = hashlib.sha256(f"{perspective}::{question}".encode("utf-8")).hexdigest()
        stance = _STANCES[int(h[0:2], 16) % len(_STANCES)]
        confidence = round(0.55 + (int(h[2:4], 16) / 255) * 0.40, 3)  # 0.55..0.95
        argument = (
            f"From a {perspective} perspective, which {description}, the question "
            f"“{question}” leans '{stance}'."
        )
        evidence = [
            {"claim": f"{perspective} consideration #{i + 1}",
             "source_kind": "reasoning",
             "note": h[4 + i * 4:8 + i * 4]}
            for i in range(2)
        ]
        return PerspectiveOutput(stance=stance, argument=argument,
                                 confidence=confidence, evidence=evidence)
