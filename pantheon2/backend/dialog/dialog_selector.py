"""
Module: dialog_selector.py
Zone: 2 (Live session — no network, no cloud calls)
Input: cache dict, ClassificationResult, ParalinguisticSignals, ObservedState
Output: SelectionResult (3 adapted options for the current moment type)
LLM calls: 0 (delegates to slm_adapter which uses local SLM only)
Side effects: None
Latency tolerance: <350ms total (SLM budget). Falls back to cache unmodified.

Retrieves cache foundations for the current moment type, then passes them
to slm_adapter for live-state adaptation (language register, urgency, framing).

The SLM is NOT optional here — it IS the live intelligence layer per PRD 4.2.
This module ensures every option the practitioner sees has been run through:
  1. Genome-calibrated foundation (cache)
  2. Live Observed State filter (slm_adapter)

If SLM times out or is unavailable, base cache options are returned unmodified —
the cache is always a valid output, never an error state.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import structlog

from backend.classifier.moment_classifier import ClassificationResult
from backend.audio.paralinguistic_extractor import ParalinguisticSignals
from backend.genome.parameter_definitions import ObservedState

logger = structlog.get_logger(__name__)

# Keys used in cache dict options blocks
_OPTION_KEYS = ("option_a", "option_b", "option_c")

# Fallback cache (returned when no cache is loaded or moment_type missing)
_HARDCODED_FALLBACK: dict = {
    "option_a": {
        "core_approach": "Acknowledge and explore",
        "base_language": "It sounds like there's something important here — can you tell me more about what's driving that?",
        "trigger_phrase": "Explore the why",
        "base_probability": 50,
        "genome_rationale": "Hardcoded fallback — cache unavailable.",
    },
    "option_b": {
        "core_approach": "Reframe toward value",
        "base_language": "Let me approach this differently — what would success look like for you in 12 months?",
        "trigger_phrase": "Reframe to value",
        "base_probability": 50,
        "genome_rationale": "Hardcoded fallback.",
    },
    "option_c": {
        "core_approach": "Build rapport",
        "base_language": "I want to make sure I understand your situation fully before we go further. What matters most to you right now?",
        "trigger_phrase": "Slow and listen",
        "base_probability": 50,
        "genome_rationale": "Hardcoded fallback.",
    },
}


@dataclass
class SelectionResult:
    """
    Output of DialogSelector.select().
    Contains the 3 adapted options (or base cache if SLM unavailable)
    for the current moment type.
    """
    moment_type: str                        # e.g. "high_openness"
    option_a: dict = field(default_factory=dict)
    option_b: dict = field(default_factory=dict)
    option_c: dict = field(default_factory=dict)
    was_adapted: bool = False               # True if SLM ran successfully
    is_cache_fallback: bool = False         # True if using hardcoded fallback (no cache)
    classification_confidence: float = 1.0  # Passed through from ClassificationResult
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class DialogSelector:
    """
    Retrieves cache foundations for the current moment type and applies
    the SLM live-state adaptation pass.

    Usage (Zone 2 event loop):
        selector = DialogSelector(cache=cache_dict, slm_adapter=slm_adapter_instance)
        result = await selector.select(classification, para, observed_state)

    Zone 2 only. No cloud calls.
    """

    def __init__(
        self,
        cache: Optional[dict] = None,
        slm_adapter=None,
    ) -> None:
        self._cache = cache or {}
        self._adapter = slm_adapter

    def update_cache(self, cache: dict) -> None:
        """
        Replace the in-memory cache. Called when Zone 1 builds a fresh cache.
        Thread-safe: replaces reference atomically (GIL-safe for dict assignment).
        """
        self._cache = cache

    async def select(
        self,
        classification: ClassificationResult,
        para: ParalinguisticSignals,
        observed_state: Optional[ObservedState] = None,
    ) -> SelectionResult:
        """
        Main entry point. Returns SelectionResult with 3 adapted options.
        Never raises — returns fallback on any error.
        """
        moment_key = classification.moment_type.value

        # Retrieve options block from cache
        base_options, is_fallback = self._get_options(moment_key)

        # Run SLM adaptation pass
        adapted_options, was_adapted = await self._adapt(
            base_options, para, observed_state
        )

        result = SelectionResult(
            moment_type=moment_key,
            option_a=adapted_options.get("option_a", {}),
            option_b=adapted_options.get("option_b", {}),
            option_c=adapted_options.get("option_c", {}),
            was_adapted=was_adapted,
            is_cache_fallback=is_fallback,
            classification_confidence=classification.confidence,
        )

        logger.debug(
            "dialog_selector.selected",
            moment=moment_key,
            was_adapted=was_adapted,
            is_fallback=is_fallback,
            confidence=round(classification.confidence, 2),
        )

        return result

    def _get_options(self, moment_key: str) -> tuple[dict, bool]:
        """
        Retrieve options block for moment_key from cache.
        Returns (options_dict, is_hardcoded_fallback).
        """
        if not self._cache:
            logger.warning("dialog_selector.no_cache", moment=moment_key)
            return copy.deepcopy(_HARDCODED_FALLBACK), True

        options = self._cache.get(moment_key)
        if not isinstance(options, dict) or not any(
            k in options for k in _OPTION_KEYS
        ):
            logger.warning(
                "dialog_selector.moment_type_missing",
                moment=moment_key,
                available=list(k for k in self._cache if not k.startswith("_")),
            )
            return copy.deepcopy(_HARDCODED_FALLBACK), True

        # Return a deep copy — never mutate the live cache
        return copy.deepcopy(options), self._cache.get("_is_fallback", False)

    async def _adapt(
        self,
        options: dict,
        para: ParalinguisticSignals,
        observed_state: Optional[ObservedState],
    ) -> tuple[dict, bool]:
        """
        Pass options through SLM adapter. Returns (adapted_options, was_adapted).
        Falls back to unmodified options if adapter unavailable.
        """
        if self._adapter is None:
            return options, False

        try:
            adapted = await self._adapter.adapt_options(
                options, para, observed_state
            )
            # Determine if adaptation actually changed anything
            was_adapted = _options_were_modified(options, adapted)
            return adapted, was_adapted
        except Exception as e:
            logger.warning("dialog_selector.adapt_error", error=str(e))
            return options, False


def _options_were_modified(original: dict, adapted: dict) -> bool:
    """
    Quick check: did the SLM actually change any base_language?
    Used only for logging — the result is always valid either way.
    """
    for key in _OPTION_KEYS:
        orig = original.get(key, {})
        mod = adapted.get(key, {})
        if orig.get("base_language") != mod.get("base_language"):
            return True
        if orig.get("base_probability") != mod.get("base_probability"):
            return True
    return False
