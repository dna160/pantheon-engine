"""
Module: divergence_detector.py
Zone: 2 (Live session — no network, no cloud calls)
Input: ClassificationResult (verbal), ParalinguisticSignals (Stream B)
Output: DivergenceAlert | None
LLM calls: 0
Side effects: None
Latency tolerance: <5ms

Fires DivergenceAlert when verbal moment classification and paralinguistic
signals contradict each other. Per PRD 3.1a:

  "When verbal and paralinguistic signals diverge, the panel fires a
   Divergence Alert: the spoken message and the physiological state are
   contradicting each other."

This is the highest-value signal in the system — particularly for high
executive_flexibility prospects who perform composure while internally activated.

Example from PRD:
  Verbal:          High Openness (prospect asking forward questions)
  Paralinguistic:  voice_tension_index HIGH, speech_rate_delta +18% above baseline
  Alert:           "Verbal openness / physiological activation mismatch.
                   Prospect is interested but under internal pressure."
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import structlog

from backend.classifier.local_classifier import MomentType
from backend.classifier.moment_classifier import ClassificationResult
from backend.audio.paralinguistic_extractor import ParalinguisticSignals

logger = structlog.get_logger(__name__)

# Thresholds for divergence detection
TENSION_HIGH_THRESHOLD: float = 0.55      # voice_tension_index above this = physiologically activated
SPEECH_RATE_SURGE_THRESHOLD: float = 0.25 # speech_rate_delta above this = rate surge
VOLUME_DROP_THRESHOLD: float = 0.25       # volume_level below this = withdrawal


@dataclass
class DivergenceAlert:
    verbal_type: MomentType
    tension_index: float
    speech_rate_delta: float
    volume_level: float
    alert_message: str
    practitioner_instruction: str
    timestamp: datetime
    severity: str  # "MODERATE" | "HIGH"


class DivergenceDetector:
    """
    Detects contradictions between verbal moment type and paralinguistic state.
    Returns DivergenceAlert when contradiction is detected, None otherwise.
    Zone 2 only. No cloud calls.
    """

    def detect(
        self,
        classification: ClassificationResult,
        para: ParalinguisticSignals,
    ) -> Optional[DivergenceAlert]:
        """
        Returns DivergenceAlert if verbal/paralinguistic contradiction detected,
        None if signals are consistent.
        """
        vtype = classification.moment_type
        tension = para.voice_tension_index
        rate_delta = para.speech_rate_delta
        volume = para.volume_level

        alert = self._check_openness_with_tension(vtype, tension, rate_delta)
        if alert:
            return alert

        alert = self._check_composure_with_withdrawal(vtype, volume, tension)
        if alert:
            return alert

        alert = self._check_closing_with_stress(vtype, tension, rate_delta)
        if alert:
            return alert

        return None

    def _check_openness_with_tension(
        self, vtype: MomentType, tension: float, rate_delta: float
    ) -> Optional[DivergenceAlert]:
        """
        PRD example: High Openness verbal + physiological activation.
        Prospect interested but under internal pressure.
        """
        if vtype != MomentType.HIGH_OPENNESS:
            return None
        if tension < TENSION_HIGH_THRESHOLD and rate_delta < SPEECH_RATE_SURGE_THRESHOLD:
            return None

        severity = "HIGH" if tension > 0.7 else "MODERATE"
        return DivergenceAlert(
            verbal_type=vtype,
            tension_index=tension,
            speech_rate_delta=rate_delta,
            volume_level=0.0,
            alert_message=(
                f"Verbal openness / physiological activation mismatch. "
                f"tension={tension:.2f}, rate_delta={rate_delta:+.2f}"
            ),
            practitioner_instruction=(
                "Prospect is interested but under internal pressure. "
                "Do NOT accelerate to close. Surface the tension first — "
                "'It sounds like there's something you're weighing up. What is it?'"
            ),
            timestamp=datetime.now(timezone.utc),
            severity=severity,
        )

    def _check_composure_with_withdrawal(
        self, vtype: MomentType, volume: float, tension: float
    ) -> Optional[DivergenceAlert]:
        """
        Verbal composure (Neutral/Exploratory) + volume drop + tension.
        Classic high executive_flexibility masking.
        """
        if vtype != MomentType.NEUTRAL_EXPLORATORY:
            return None
        if volume >= VOLUME_DROP_THRESHOLD or tension < TENSION_HIGH_THRESHOLD:
            return None

        return DivergenceAlert(
            verbal_type=vtype,
            tension_index=tension,
            speech_rate_delta=0.0,
            volume_level=volume,
            alert_message=(
                f"Verbal composure / physiological withdrawal mismatch. "
                f"volume={volume:.2f}, tension={tension:.2f}"
            ),
            practitioner_instruction=(
                "Prospect appears composed verbally but volume is dropping and tension rising. "
                "High executive_flexibility masking likely. Slow down, ask an open question, "
                "and create explicit space: 'Is there something on your mind we haven't addressed?'"
            ),
            timestamp=datetime.now(timezone.utc),
            severity="HIGH",
        )

    def _check_closing_with_stress(
        self, vtype: MomentType, tension: float, rate_delta: float
    ) -> Optional[DivergenceAlert]:
        """
        Verbal closing signal + physiological stress — prospect wants to proceed
        but is experiencing internal conflict (fear, doubt, authority constraint).
        """
        if vtype != MomentType.CLOSING_SIGNAL:
            return None
        if tension < TENSION_HIGH_THRESHOLD:
            return None

        return DivergenceAlert(
            verbal_type=vtype,
            tension_index=tension,
            speech_rate_delta=rate_delta,
            volume_level=0.0,
            alert_message=(
                f"Verbal closing signal / physiological stress mismatch. "
                f"tension={tension:.2f}"
            ),
            practitioner_instruction=(
                "Prospect is signaling interest but under stress. Do not push for commitment now. "
                "Acknowledge the decision weight: 'This is a significant step — what would make "
                "you feel most confident moving forward?'"
            ),
            timestamp=datetime.now(timezone.utc),
            severity="MODERATE",
        )
