"""
Module: slm_classifier.py
Zone: 2 (Live session — no network, no cloud calls)
Input: transcript text + ObservedState
Output: (MomentType, confidence float)
LLM calls: 0 (local SLM only — never cloud)
Side effects: None
Latency tolerance: <250ms (SLM inference budget)

SLM fallback classifier. Used when local_classifier confidence is below
threshold. Delegates to slm_runner with a classification prompt.
If SLM times out (>350ms hard limit), falls back to NEUTRAL_EXPLORATORY.
"""

from __future__ import annotations

import json
import re

import structlog

from backend.classifier.local_classifier import MomentType

logger = structlog.get_logger(__name__)

_CLASSIFICATION_PROMPT_TEMPLATE = """Classify this sales conversation segment into exactly one of these 6 moment types:
neutral_exploratory, irate_resistant, topic_avoidance, identity_threat, high_openness, closing_signal

Transcript: {text}

Context: Indonesian B2B advisory conversation.
Irate signals are often indirect in Indonesian context (over-politeness, "ya betul" flooding).
Closing signals may be indirect ("boleh minta proposal?", "kapan bisa mulai?").

Respond with ONLY a JSON object: {{"moment_type": "<type>", "confidence": <0.0-1.0>}}"""


class SLMClassifier:
    """
    SLM-backed moment classifier. Falls back to NEUTRAL_EXPLORATORY on timeout.
    Zone 2 only. No cloud calls.
    """

    def __init__(self, slm_runner=None) -> None:
        self._runner = slm_runner  # injected by moment_classifier

    def classify(self, text: str) -> tuple[MomentType, float]:
        """
        Synchronous SLM classification.
        Returns (NEUTRAL_EXPLORATORY, 0.3) if SLM unavailable or timeout.
        """
        if self._runner is None:
            return MomentType.NEUTRAL_EXPLORATORY, 0.3

        prompt = _CLASSIFICATION_PROMPT_TEMPLATE.format(text=text[:500])

        try:
            raw = self._runner.run_sync(prompt)
            return self._parse(raw)
        except Exception as e:
            logger.warning("slm_classifier.error", error=str(e))
            return MomentType.NEUTRAL_EXPLORATORY, 0.3

    def _parse(self, raw: str) -> tuple[MomentType, float]:
        try:
            clean = re.sub(r"```(?:json)?\s*|\s*```", "", raw).strip()
            data = json.loads(clean)
            mt = MomentType(data.get("moment_type", "neutral_exploratory"))
            confidence = float(data.get("confidence", 0.5))
            return mt, min(1.0, max(0.0, confidence))
        except Exception:
            return MomentType.NEUTRAL_EXPLORATORY, 0.3
