"""Provider selection defaults to deterministic; opts into ollama explicitly."""

import unittest

from council_mcp.config import Config
from council_mcp.council import (
    DeterministicDemoProvider,
    FallbackProvider,
    select_provider,
)


class SelectProviderTest(unittest.TestCase):
    def test_default_is_deterministic(self):
        self.assertIsInstance(select_provider(Config()), DeterministicDemoProvider)

    def test_unknown_value_falls_back_to_deterministic(self):
        cfg = Config(reasoning_provider="something-else")
        self.assertIsInstance(select_provider(cfg), DeterministicDemoProvider)

    def test_ollama_selection_is_wrapped_in_fallback(self):
        cfg = Config(reasoning_provider="ollama")
        provider = select_provider(cfg)
        self.assertIsInstance(provider, FallbackProvider)
        # The fallback is the deterministic provider.
        self.assertIsInstance(provider.fallback, DeterministicDemoProvider)

    def test_env_parsing(self):
        cfg = Config.from_env({"REASONING_PROVIDER": "ollama",
                               "OLLAMA_MODEL": "mistral",
                               "OLLAMA_URL": "http://localhost:9999"})
        self.assertEqual(cfg.reasoning_provider, "ollama")
        self.assertEqual(cfg.ollama_model, "mistral")
        self.assertEqual(cfg.ollama_url, "http://localhost:9999")

    def test_default_env_is_deterministic(self):
        self.assertEqual(Config.from_env({}).reasoning_provider, "deterministic")


if __name__ == "__main__":
    unittest.main()
