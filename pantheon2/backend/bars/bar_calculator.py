"""
Module: bar_calculator.py
Zone: 2 (Live session — no network, no cloud calls)
Input: ClassificationResult, ParalinguisticSignals, Genome
Output: BarState (hook_score 0–100, close_score 0–100)
LLM calls: 0
Side effects: None
Latency tolerance: <5ms

Hook bar: measures attention activation — rising with engagement signals,
falling with resistance, avoidance, identity threat.

Close bar: measures decision proximity — rising with openness and closing signals,
falling with avoidance, resistance, high tension without verbal openness.

Both streams contribute (PRD CLAUDE.md Zone 2 workflow):
- Verbal moment type drives primary direction
- Paralinguistic signals modulate (divergence can raise OR lower bars)

Genome modifiers per PRD 3.3 / SKILL.md probability rules:
- executive_flexibility > 70: bars decay more slowly (surface composure unreliable)
- neuroticism HIGH: close_bar suppressed under resistance moments
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import structlog

from backend.classifier.local_classifier import MomentType
from backend.classifier.moment_classifier import ClassificationResult
from backend.audio.paralinguistic_extractor import ParalinguisticSignals
from backend.genome.parameter_definitions import Genome

logger = structlog.get_logger(__name__)

# Score clamp bounds
MIN_SCORE: int = 0
MAX_SCORE: int = 100

# Decay / rise step sizes per event
_MOMENT_HOOK_DELTA: dict[MomentType, int] = {
    MomentType.NEUTRAL_EXPLORATORY: +3,
    MomentType.HIGH_OPENNESS:       +12,
    MomentType.CLOSING_SIGNAL:      +8,
    MomentType.IRATE_RESISTANT:     -10,
    MomentType.TOPIC_AVOIDANCE:     -6,
    MomentType.IDENTITY_THREAT:     -8,
}

_MOMENT_CLOSE_DELTA: dict[MomentType, int] = {
    MomentType.NEUTRAL_EXPLORATORY: +2,
    MomentType.HIGH_OPENNESS:       +8,
    MomentType.CLOSING_SIGNAL:      +15,
    MomentType.IRATE_RESISTANT:     -8,
    MomentType.TOPIC_AVOIDANCE:     -5,
    MomentType.IDENTITY_THREAT:     -10,
}


@dataclass
class BarState:
    hook_score: int = 50
    close_score: int = 30   # Close starts lower — must be earned
    hook_trend: str = "stable"   # "rising" | "falling" | "stable"
    close_trend: str = "stable"


class BarCalculator:
    """
    Maintains Hook and Close bar scores across the session.
    Updated on every classification event + paralinguistic snapshot.
    Zone 2 only. No cloud calls.
    """

    def __init__(self, genome: Optional[Genome] = None) -> None:
        self._state = BarState()
        self._genome = genome
        self._prev_hook = 50
        self._prev_close = 30

    def update(
        self,
        classification: ClassificationResult,
        para: ParalinguisticSignals,
    ) -> BarState:
        """
        Update bars from classification + paralinguistic signals.
        Returns updated BarState.
        """
        mtype = classification.moment_type

        # Base deltas from moment type
        hook_delta = _MOMENT_HOOK_DELTA.get(mtype, 0)
        close_delta = _MOMENT_CLOSE_DELTA.get(mtype, 0)

        # Paralinguistic modulation
        hook_delta, close_delta = self._apply_para_modulation(
            hook_delta, close_delta, para, mtype
        )

        # Genome modifiers
        if self._genome:
            hook_delta, close_delta = self._apply_genome_modifiers(
                hook_delta, close_delta, mtype
            )

        # Apply confidence scaling — low-confidence classifications have smaller effect
        conf = classification.confidence
        hook_delta = int(hook_delta * conf)
        close_delta = int(close_delta * conf)

        # Update scores
        self._prev_hook = self._state.hook_score
        self._prev_close = self._state.close_score

        new_hook = max(MIN_SCORE, min(MAX_SCORE, self._state.hook_score + hook_delta))
        new_close = max(MIN_SCORE, min(MAX_SCORE, self._state.close_score + close_delta))

        self._state = BarState(
            hook_score=new_hook,
            close_score=new_close,
            hook_trend=self._trend(new_hook, self._prev_hook),
            close_trend=self._trend(new_close, self._prev_close),
        )

        logger.debug(
            "bar_calculator.updated",
            moment=mtype.value,
            hook=new_hook,
            close=new_close,
            hook_trend=self._state.hook_trend,
        )

        return self._state

    def _apply_para_modulation(
        self,
        hook_delta: int,
        close_delta: int,
        para: ParalinguisticSignals,
        mtype: MomentType,
    ) -> tuple[int, int]:
        """
        Paralinguistic modulation: tension, volume, rate affect magnitude.
        Per PRD 3.1a — paralinguistics carry independent signal value.
        """
        # High tension on positive moments: dampens close bar (prospect activated not relaxed)
        if mtype in (MomentType.HIGH_OPENNESS, MomentType.CLOSING_SIGNAL):
            if para.voice_tension_index > 0.6:
                close_delta = int(close_delta * 0.5)

        # Volume drop: withdrawal signal — dampen positive effects
        if para.volume_level < 0.25:
            hook_delta = int(hook_delta * 0.6)
            close_delta = int(close_delta * 0.5)

        # Very long pause after practitioner speaks: genuine deliberation — hold close bar
        if para.pause_duration > 4.0:
            close_delta = max(close_delta, 0)  # don't drop close during genuine thinking

        # Rate surge on resistance: amplifies negative signal
        if mtype == MomentType.IRATE_RESISTANT and para.speech_rate_delta > 0.25:
            hook_delta = int(hook_delta * 1.3)

        return hook_delta, close_delta

    def _apply_genome_modifiers(
        self, hook_delta: int, close_delta: int, mtype: MomentType
    ) -> tuple[int, int]:
        g = self._genome

        # High executive_flexibility: surface signals unreliable — dampen all bar movements
        if g.executive_flexibility is not None and g.executive_flexibility > 70:
            hook_delta = int(hook_delta * 0.7)
            close_delta = int(close_delta * 0.7)

        # High neuroticism + resistance: stronger negative effect
        if (
            g.neuroticism is not None and g.neuroticism > 65
            and mtype == MomentType.IRATE_RESISTANT
        ):
            close_delta = int(close_delta * 1.4)

        # High chronesthesia: vision hooks land — boost HIGH_OPENNESS close bar
        if (
            g.chronesthesia_capacity is not None and g.chronesthesia_capacity > 65
            and mtype == MomentType.HIGH_OPENNESS
        ):
            close_delta = int(close_delta * 1.2)

        # High identity_fusion + identity threat: amplify negative
        if (
            g.identity_fusion is not None and g.identity_fusion > 65
            and mtype == MomentType.IDENTITY_THREAT
        ):
            hook_delta = int(hook_delta * 1.3)

        return hook_delta, close_delta

    @staticmethod
    def _trend(new: int, old: int) -> str:
        if new > old + 2:
            return "rising"
        if new < old - 2:
            return "falling"
        return "stable"

    @property
    def state(self) -> BarState:
        return self._state
