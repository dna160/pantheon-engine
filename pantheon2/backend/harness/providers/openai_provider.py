"""
Module: openai_provider.py
Zone: 1 and 3 (never Zone 2)
Input: prompt, system, config
Output: str (raw completion text)
LLM calls: 1 per call (OpenAI Chat Completions API)
Side effects: Network call, API key usage
Latency tolerance: 5–30 seconds
"""

from __future__ import annotations

import os
import structlog
from openai import AsyncOpenAI

logger = structlog.get_logger(__name__)


class OpenAIProvider:
    """OpenAI Chat Completions provider."""

    def __init__(self) -> None:
        self._client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

    async def complete(self, prompt: str, system: str, config) -> str:
        model = getattr(config, "model", "gpt-4o")
        max_tokens = getattr(config, "max_tokens", 2000)
        temperature = getattr(config, "temperature", 0.3)

        logger.info("openai_provider.call", model=model)

        response = await self._client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content or ""
