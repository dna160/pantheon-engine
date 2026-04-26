"""
Module: lmstudio_provider.py
Zone: 1 and 3 (never Zone 2 — Zone 2 uses llama_cpp directly, not via HTTP)
Input: prompt, system, config
Output: str (raw completion text)
LLM calls: 1 per call (LM Studio OpenAI-compatible endpoint)
Side effects: Network call to localhost LM Studio server
Latency tolerance: 10–60 seconds (local inference)

Config: set provider="lmstudio", model="http://localhost:1234/v1"
No API key required for local LM Studio.
"""

from __future__ import annotations

import structlog
from openai import AsyncOpenAI

logger = structlog.get_logger(__name__)

DEFAULT_LMSTUDIO_URL = "http://localhost:1234/v1"


class LMStudioProvider:
    """LM Studio OpenAI-compatible endpoint provider."""

    async def complete(self, prompt: str, system: str, config) -> str:
        # model field holds the server URL for lmstudio
        base_url = getattr(config, "model", DEFAULT_LMSTUDIO_URL)
        if not base_url.startswith("http"):
            base_url = DEFAULT_LMSTUDIO_URL

        max_tokens = getattr(config, "max_tokens", 2000)
        temperature = getattr(config, "temperature", 0.3)

        logger.info("lmstudio_provider.call", base_url=base_url)

        client = AsyncOpenAI(base_url=base_url, api_key="lm-studio")
        response = await client.chat.completions.create(
            model="local-model",
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content or ""
