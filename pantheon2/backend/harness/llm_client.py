"""
Module: llm_client.py
Zone: 1 and 3 (never Zone 2)
Input: prompt str, system str, ProviderConfig
Output: str (raw LLM response)
LLM calls: delegates to provider implementations
Side effects: Network call to configured LLM provider
Latency tolerance: 5–60 seconds (Zone 1/3 only)

Provider-agnostic completion client. Swap providers by editing harness.config.json.
All providers return raw str. JSON parsing happens in the calling module (cache_builder, session_analyzer).
"""

from __future__ import annotations

import structlog

logger = structlog.get_logger(__name__)


class LLMClient:
    """
    Factory-based provider-agnostic LLM client.
    Routes to the correct provider implementation based on config.provider.
    """

    async def complete(self, prompt: str, system: str, config) -> str:
        """
        Routes completion to the appropriate provider.
        config: Zone1Config | Zone3Config | PsychReviewConfig — any with .provider and .model
        """
        provider_name = getattr(config, "provider", "anthropic")
        logger.info(
            "llm_client.complete",
            provider=provider_name,
            model=getattr(config, "model", "unknown"),
        )

        provider = self._get_provider(provider_name)
        return await provider.complete(prompt=prompt, system=system, config=config)

    def _get_provider(self, provider_name: str):
        if provider_name == "anthropic":
            from backend.harness.providers.anthropic_provider import AnthropicProvider
            return AnthropicProvider()
        elif provider_name == "openai":
            from backend.harness.providers.openai_provider import OpenAIProvider
            return OpenAIProvider()
        elif provider_name == "gemini":
            from backend.harness.providers.gemini_provider import GeminiProvider
            return GeminiProvider()
        elif provider_name == "lmstudio":
            from backend.harness.providers.lmstudio_provider import LMStudioProvider
            return LMStudioProvider()
        else:
            raise ValueError(
                f"Unknown provider: {provider_name}. "
                "Supported: anthropic, openai, gemini, lmstudio"
            )
