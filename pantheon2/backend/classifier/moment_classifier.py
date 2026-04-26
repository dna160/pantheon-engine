"""
Module: moment_classifier.py
Zone: 2 (Live session — no network, no cloud calls)
Input: TranscriptionResult, elapsed_session_seconds
Output: ClassificationResult (MomentType, confidence, path)
LLM calls: 0 (local SLM only if local_classifier confidence low)
Side effects: None
Latency tolerance: <10ms (local path) | <250ms (SLM path)

Dispatcher: tries LocalClassifier first (<10ms, rule-based).
If confidence < LOCAL_CONFIDENCE_THRESHOLD, falls back to SLMClassifier.
If SLM times out, uses local result regardless of confidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import structlog

from backend.classifier.local_classifier import LocalClassifier, MomentType
from backend.classifier.slm_classifier import SLMClassifier
from backend.audio.transcription_engine import TranscriptionResult

logger = structlog.get_logger(__name__)

LOCAL_CONFIDENCE_THRESHOLD = 0.45   # Below this → try SLM


@dataclass
class ClassificationResult:
    moment_type: MomentType
    confidence: float              # 0.0–1.0
    path: str                      # "local" | "slm" | "fallback"
    text_snippet: str              # first 80 chars of transcript segment
    timestamp: datetime


class MomentClassifier:
    """
    Dispatcher for 6-type moment classification.
    Local first, SLM fallback, hard fallback to NEUTRAL_EXPLORATORY.
    Zone 2 only. No cloud calls.
    """

    def __init__(self, slm_runner=None) -> None:
        self._local = LocalClassifier()
        self._slm = SLMClassifier(slm_runner=slm_runner)

    def classify(
        self,
        result: TranscriptionResult,
        elapsed_session_seconds: float = 999.0,
    ) -> ClassificationResult:
        """
        Classify a transcription result. Synchronous (Zone 2 loop calls this).
        """
        text = result.text.strip()

        if not text:
            return ClassificationResult(
                moment_type=MomentType.NEUTRAL_EXPLORATORY,
                confidence=0.3,
                path="fallback",
                text_snippet="",
                timestamp=result.timestamp,
            )

        # Step 1: Local classifier (<10ms)
        local_type, local_conf = self._local.classify(text, elapsed_session_seconds)

        if local_conf >= LOCAL_CONFIDENCE_THRESHOLD:
            logger.debug(
                "moment_classifier.local",
                type=local_type.value,
                confidence=round(local_conf, 2),
            )
            return ClassificationResult(
                moment_type=local_type,
                confidence=local_conf,
                path="local",
                text_snippet=text[:80],
                timestamp=result.timestamp,
            )

        # Step 2: SLM fallback (<250ms)
        slm_type, slm_conf = self._slm.classify(text)

        # Use SLM result if it's more confident
        if slm_conf > local_conf:
            logger.debug(
                "moment_classifier.slm",
                type=slm_type.value,
                confidence=round(slm_conf, 2),
            )
            return ClassificationResult(
                moment_type=slm_type,
                confidence=slm_conf,
                path="slm",
                text_snippet=text[:80],
                timestamp=result.timestamp,
            )

        # Return local result even at low confidence
        return ClassificationResult(
            moment_type=local_type,
            confidence=local_conf,
            path="local",
            text_snippet=text[:80],
            timestamp=result.timestamp,
        )
