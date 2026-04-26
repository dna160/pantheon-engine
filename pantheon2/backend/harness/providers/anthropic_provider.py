"""
Module: anthropic_provider.py
Zone: 1 and 3 (never Zone 2)
Input: prompt, system, Zone1Config | Zone3Config | PsychReviewConfig
Output: str (raw completion text)
LLM calls: 1 per call (Anthropic Messages API with prompt caching)
Side effects: Network call, API key usage
Latency tolerance: 5–30 seconds
"""

from __future__ import annotations

import os
import structlog
import anthropic

logger = structlog.get_logger(__name__)


class AnthropicProvider:
    """Anthropic Messages API provider with prompt caching on system prompt."""

    def __init__(self) -> None:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    async def complete(self, prompt: str, system: str, config) -> str:
        model = getattr(config, "model", "claude-sonnet-4-6")
        max_tokens = getattr(config, "max_tokens", 2000)
        temperature = getattr(config, "temperature", 0.3)

        logger.info("anthropic_provider.call", model=model, max_tokens=max_tokens)

        message = await self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=[
                {
                    "type": "text",
                    "text": system,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": prompt}],
        )

        raw = message.content[0].text
        logger.info(
            "anthropic_provider.response",
            input_tokens=message.usage.input_tokens,
            output_tokens=message.usage.output_tokens,
            cache_read=getattr(message.usage, "cache_read_input_tokens", 0),
        )
        return raw
