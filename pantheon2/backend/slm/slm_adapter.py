"""
Module: slm_adapter.py
Zone: 2 (Live session — no network, no cloud calls)
Input: cache foundations (3 options) + ObservedState (full)
Output: adapted options (same structure, framing adjusted)
LLM calls: 0 (local SLM only — NEVER cloud)
Side effects: None
Latency tolerance: <200ms target, <350ms hard limit. Falls back to base cache unmodified.

THE LIVE INTELLIGENCE LAYER (PRD 4.2).

The SLM is not a fallback. It is the live-state adaptation engine.
Every option the practitioner sees has passed through both:
  1. The genome-calibrated cache foundation (genome-grounded starting position)
  2. This adapter (live Observed State filter)

The SLM adjusts HOW each foundation is expressed right now, based on:
  - language register (more/less formal) from cadence signals
  - urgency adjustment from voice_tension_index
  - approach framing from live sentiment drift
  - probability adjustment from current paralinguistic state

The SLM does NOT rewrite strategic direction — cache owns that.
The SLM ONLY adjusts how the direction is expressed right now.
"""

from __future__ import annotations

import asyncio
import copy
import json
import re
from typing import Optional

import structlog

from backend.audio.paralinguistic_extractor import ParalinguisticSignals
from backend.genome.parameter_definitions import ObservedState

logger = structlog.get_logger(__name__)

_ADAPTATION_PROMPT_TEMPLATE = """You are adapting a pre-computed sales dialog option for the CURRENT moment in a conversation.

GENOME-CALIBRATED FOUNDATION:
{option_json}

CURRENT OBSERVED STATE:
- voice_tension_index: {tension} (0=calm, 1=highly activated)
- speech_rate_delta: {rate_delta:+.2f} (negative=slowing, positive=speeding up vs baseline)
- volume_level: {volume:.2f} (0=withdrawing, 1=engaged)
- pause_duration: {pause:.1f}s (silence after last utterance)
- cadence_consistency: {cadence:.2f} (1=rhythmic, 0=broken)
- current_sentiment: {sentiment}

ADAPTATION RULES:
- If tension > 0.6: soften urgency, add acknowledgment of pressure before content
- If speech_rate_delta > 0.2: prospect is activated — match energy, keep it brief
- If speech_rate_delta < -0.2: prospect is withdrawing — slow down, open space
- If pause_duration > 4.0: genuine deliberation — do NOT fill silence
- If cadence broken (< 0.4): prospect managing face or masking — be gentler
- Do NOT change the strategic direction of the option
- ONLY adjust language register, urgency, and how the approach is introduced
- Keep output under 2 sentences

Respond ONLY with JSON: {{"base_language": "<adapted text>", "base_probability": <INT 0-100>}}"""


class SLMAdapter:
    """
    Adapts genome-calibrated cache foundations against current Observed State.
    Falls back to base cache option unmodified if SLM times out or errors.
    Zone 2 only. No cloud calls.
    """

    def __init__(self, slm_runner=None) -> None:
        self._runner = slm_runner

    async def adapt_options(
        self,
        options: dict,
        para: ParalinguisticSignals,
        observed_state: Optional[ObservedState] = None,
    ) -> dict:
        """
        Adapt all 3 options in a moment-type cache block.
        Returns adapted options dict. Falls back to original on timeout/error.
        """
        if self._runner is None or not self._runner.is_loaded:
            return options  # No SLM → return cache unmodified

        adapted = copy.deepcopy(options)
        sentiment = self._extract_sentiment(observed_state)

        # Adapt each option concurrently within the 350ms budget
        tasks = {}
        for key in ("option_a", "option_b", "option_c"):
            option = adapted.get(key)
            if not isinstance(option, dict):
                continue
            tasks[key] = asyncio.create_task(
                self._adapt_single(option, para, sentiment)
            )

        for key, task in tasks.items():
            try:
                result = await asyncio.wait_for(task, timeout=0.35)
                if result:
                    adapted[key].update(result)
            except asyncio.TimeoutError:
                logger.warning("slm_adapter.timeout", option=key)
                # Falls back to unmodified option
            except Exception as e:
                logger.warning("slm_adapter.error", option=key, error=str(e))

        return adapted

    async def _adapt_single(
        self, option: dict, para: ParalinguisticSignals, sentiment: str
    ) -> Optional[dict]:
        prompt = _ADAPTATION_PROMPT_TEMPLATE.format(
            option_json=json.dumps({
                "core_approach": option.get("core_approach", ""),
                "base_language": option.get("base_language", ""),
            }),
            tension=para.voice_tension_index,
            rate_delta=para.speech_rate_delta,
            volume=para.volume_level,
            pause=para.pause_duration,
            cadence=para.cadence_consistency_score,
            sentiment=sentiment,
        )

        raw = await self._runner.run(prompt)
        if not raw:
            return None

        return self._parse(raw)

    def _parse(self, raw: str) -> Optional[dict]:
        try:
            clean = re.sub(r"```(?:json)?\s*|\s*```", "", raw).strip()
            data = json.loads(clean)
            result = {}
            if "base_language" in data and isinstance(data["base_language"], str):
                result["base_language"] = data["base_language"]
            if "base_probability" in data:
                prob = int(data["base_probability"])
                result["base_probability"] = max(10, min(90, prob))
            return result if result else None
        except Exception:
            return None

    def _extract_sentiment(self, observed_state: Optional[ObservedState]) -> str:
        if observed_state is None:
            return "neutral"
        # ObservedState has sentiment field from verbal stream
        sentiment = getattr(observed_state, "sentiment", None)
        if sentiment:
            return str(sentiment)
        return "neutral"
