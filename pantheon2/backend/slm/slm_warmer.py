"""
Module: slm_warmer.py
Zone: 1 (Pre-session — runs during Zone 1 setup, parallel with cache build)
Input: Zone2Config
Output: WarmUpResult (latency_ms, success)
LLM calls: 0 (local model only)
Side effects: Loads model into memory; fills slm_runner._llm
Latency tolerance: N/A — runs async in background during Zone 1

Pre-loads local SLM and runs a dummy inference to warm up the model.
Per PRD: "Run warm-up inference (dummy input). Confirm <250ms cold inference latency."
Called from harness_runner._warm_slm() as fire-and-forget task.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

import structlog

from backend.slm.slm_config import SLMConfig
from backend.slm.slm_runner import SLMRunner

logger = structlog.get_logger(__name__)

_WARMUP_PROMPT = (
    'Classify: "Tell me more about that." '
    'Options: neutral_exploratory, irate_resistant, topic_avoidance, '
    'identity_threat, high_openness, closing_signal. '
    'JSON only: {"moment_type": "<type>", "confidence": 0.8}'
)


@dataclass
class WarmUpResult:
    success: bool
    latency_ms: float
    model_path: str
    message: str


class SLMWarmer:
    """
    Pre-loads the local SLM and measures cold inference latency.
    Runs in background during Zone 1 (does not block session start).
    Zone 1 only — Zone 2 uses the already-warmed runner.
    """

    def __init__(self, zone2_config) -> None:
        self._config = SLMConfig.from_zone2_config(zone2_config)
        self._runner: Optional[SLMRunner] = None

    async def warm_up(self) -> WarmUpResult:
        """
        Load model + run dummy inference to warm up.
        Returns WarmUpResult — never raises.
        """
        runner = SLMRunner(self._config)

        t0 = time.monotonic()
        loaded = runner.load()
        if not loaded:
            return WarmUpResult(
                success=False,
                latency_ms=0.0,
                model_path=self._config.model_path,
                message="Model file not found or llama-cpp not installed — stub mode active",
            )

        # Dummy inference to warm up
        _ = runner._infer(_WARMUP_PROMPT)
        latency_ms = (time.monotonic() - t0) * 1000.0

        self._runner = runner

        if latency_ms > 250:
            logger.warning(
                "slm_warmer.latency_exceeds_target",
                latency_ms=round(latency_ms, 1),
                target_ms=250,
            )
        else:
            logger.info(
                "slm_warmer.warm_up_ok",
                latency_ms=round(latency_ms, 1),
            )

        return WarmUpResult(
            success=True,
            latency_ms=round(latency_ms, 1),
            model_path=self._config.model_path,
            message=f"SLM warm-up complete. Cold inference: {latency_ms:.0f}ms",
        )

    @property
    def runner(self) -> Optional[SLMRunner]:
        """Returns the warmed runner for injection into MomentClassifier / SLMAdapter."""
        return self._runner
