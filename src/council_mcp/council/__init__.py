"""Concept A — the Deliberation Council (Phase 2A).

  * provider     — ReasoningProvider interface + DeterministicDemoProvider (default)
  * perspectives — the independent viewpoints and their evaluation
  * synthesis    — compose a recommendation with preserved dissent
  * engine       — run_deliberation: orchestration + the deliberation state machine
  * service      — CouncilService: start / get / cancel (request-path)

State machine: QUEUED -> RUNNING -> SYNTHESIZING -> COMPLETED, with FAILED
(unexpected error) and CANCELLED (owner request) from any non-terminal state.
The deliberation runs as a single background job; cancellation is cooperative,
enforced by optimistic status guards at each transition.
"""

from .provider import DeterministicDemoProvider, ReasoningProvider, PerspectiveOutput
from .ollama_provider import FallbackProvider, OllamaProvider
from .factory import select_provider
from .service import CouncilService
from .engine import run_deliberation

__all__ = [
    "ReasoningProvider",
    "DeterministicDemoProvider",
    "PerspectiveOutput",
    "OllamaProvider",
    "FallbackProvider",
    "select_provider",
    "CouncilService",
    "run_deliberation",
]
