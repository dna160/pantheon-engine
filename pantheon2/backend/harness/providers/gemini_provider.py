"""
Module: gemini_provider.py
Zone: 1 and 3 (never Zone 2)
Input: prompt, system, config
Output: str (raw completion text)
LLM calls: 1 per call (Google Gemini API — sync wrapped in asyncio executor)
Side effects: Network call, API key usage
Latency tolerance: 5–30 seconds
"""

from __future__ import annotations

import asyncio
import os
import structlog

logger = structlog.get_logger(__name__)


class GeminiProvider:
    """Google Gemini provider. Sync SDK wrapped in executor for async compatibility."""

    async def complete(self, prompt: str, system: str, config) -> str:
        model = getattr(config, "model", "gemini-1.5-pro")
        max_tokens = getattr(config, "max_tokens", 2000)
        temperature = getattr(config, "temperature", 0.3)

        logger.info("gemini_provider.call", model=model)

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self._sync_complete(prompt, system, model, max_tokens, temperature),
        )

    def _sync_complete(
        self,
        prompt: str,
        system: str,
        model: str,
        max_tokens: int,
        temperature: float,
    ) -> str:
        import google.generativeai as genai
        genai.configure(api_key=os.environ.get("GEMINI_API_KEY", ""))
        gemini_model = genai.GenerativeModel(
            model_name=model,
            system_instruction=system,
            generation_config=genai.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
            ),
        )
        response = gemini_model.generate_content(prompt)
        return response.text
