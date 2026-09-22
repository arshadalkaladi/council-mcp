"""Provider selection.

Default is the certified, offline, zero-cost DeterministicDemoProvider. Only an
explicit configuration opts into an optional provider, and even then the optional
provider is wrapped so any failure falls back to deterministic reasoning.
"""

from __future__ import annotations

from .provider import DeterministicDemoProvider, ReasoningProvider
from .ollama_provider import FallbackProvider, OllamaProvider


def select_provider(config) -> ReasoningProvider:
    kind = (getattr(config, "reasoning_provider", "deterministic") or "deterministic").lower()
    if kind == "ollama":
        primary = OllamaProvider(config.ollama_url, config.ollama_model)
        return FallbackProvider(primary, DeterministicDemoProvider())
    # default and any unknown value -> deterministic (safe default)
    return DeterministicDemoProvider()
