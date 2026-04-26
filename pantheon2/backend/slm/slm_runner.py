"""
Module: slm_runner.py
Zone: 2 (Live session — no network, no cloud calls)
Input: prompt string
Output: raw string response
LLM calls: 0 (local model only — NEVER cloud)
Side effects: None
Latency tolerance: <350ms hard limit (asyncio.wait_for enforced)

Local SLM inference runner with 350ms hard timeout per PRD 4.2.
Uses llama-cpp-python if model file exists; returns empty string stub otherwise.
Timeout is enforced via asyncio.wait_for — caller receives "" on timeout
and must fall back to base cache unmodified.
"""

from __future__ import annotations

import asyncio
from typing import Optional

import structlog

from backend.slm.slm_config import SLMConfig

logger = structlog.get_logger(__name__)


class SLMRunner:
    """
    Local SLM inference with 350ms hard timeout.
    Zone 2 only. No cloud calls ever.
    """

    def __init__(self, config: SLMConfig) -> None:
        self._config = config
        self._llm = None   # lazy-loaded

    def load(self) -> bool:
        """
        Load the model into memory. Called by slm_warmer.py pre-session.
        Returns True if model loaded, False if model file not found (stub mode).
        """
        if not self._config.model_exists:
            logger.warning(
                "slm_runner.model_not_found",
                path=self._config.model_path,
                note="Running in stub mode — will return empty string",
            )
            return False

        try:
            from llama_cpp import Llama  # type: ignore
            self._llm = Llama(
                model_path=self._config.model_path,
                n_ctx=2048,
                n_threads=4,
                n_gpu_layers=-1,   # Use GPU if available
                verbose=False,
            )
            logger.info("slm_runner.loaded", path=self._config.model_path)
            return True
        except ImportError:
            logger.warning("slm_runner.llama_cpp_not_installed — stub mode")
            return False
        except Exception as e:
            logger.error("slm_runner.load_failed", error=str(e))
            return False

    async def run(self, prompt: str) -> str:
        """
        Async inference with 350ms hard timeout.
        Returns "" on timeout or error — caller must use cache fallback.
        """
        timeout_s = self._config.timeout_ms / 1000.0
        try:
            result = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None, self._infer, prompt
                ),
                timeout=timeout_s,
            )
            return result
        except asyncio.TimeoutError:
            logger.warning("slm_runner.timeout", timeout_ms=self._config.timeout_ms)
            return ""
        except Exception as e:
            logger.warning("slm_runner.error", error=str(e))
            return ""

    def run_sync(self, prompt: str) -> str:
        """
        Synchronous inference (used by slm_classifier.py which runs in executor).
        Returns "" on any failure.
        """
        return self._infer(prompt)

    def _infer(self, prompt: str) -> str:
        if self._llm is None:
            return ""
        try:
            output = self._llm(
                prompt,
                max_tokens=self._config.max_tokens,
                temperature=self._config.temperature,
                stop=["```", "\n\n\n"],
            )
            return output["choices"][0]["text"].strip()
        except Exception as e:
            logger.warning("slm_runner.infer_error", error=str(e))
            return ""

    @property
    def is_loaded(self) -> bool:
        return self._llm is not None
