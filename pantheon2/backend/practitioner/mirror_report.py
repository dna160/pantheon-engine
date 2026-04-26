"""
Module: mirror_report.py
Zone: 3 (Post-session only — NEVER shown on live HUD)
Input: SessionAnalysisResult, PractitionerProfile
Output: MirrorReportPayload (4 observations + trend context)
LLM calls: 0
Side effects: None
Latency tolerance: N/A (post-session, async)

Mirror Report renderer for the practitioner.

CRITICAL CONSTRAINT (PRD CLAUDE.md #6):
  NOTHING from this module appears on the live Zone 2 HUD.
  This is hardcoded — not configurable. The Mirror Report is post-session only.
  Mobile app renders it in MirrorReportScreen.tsx only after session ends.

What the Mirror Report shows (4 observations, per zone3_session_analyzer.txt):
  1. signature_strength — moment type where Hook/Close delta was consistently highest
  2. blind_spot — specific avoidance pattern with highest cost (missed windows, suppressed bars)
  3. instinct_ratio — override_success_rate with directional guidance
  4. pressure_signature — specific behavior under Irate/Identity Threat moments

Plus: trend context from PractitionerProfile (session count, trajectory vs. previous sessions).
Language: honest, direct. Not clinical. No hedging for findings with clear behavioral evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import structlog

from backend.session.session_analyzer import SessionAnalysisResult, MirrorReport
from backend.practitioner.practitioner_profile import PractitionerProfile

logger = structlog.get_logger(__name__)

# Score thresholds for trend tagging
STRENGTH_THRESHOLD = 65.0       # Above this → "performing well"
DEVELOPMENT_THRESHOLD = 40.0    # Below this → "development area"
TREND_DELTA_SIGNIFICANT = 5.0   # Score change > 5 pts across sessions = meaningful trend


@dataclass
class MirrorReportPayload:
    """
    Full Mirror Report payload for the mobile app MirrorReportScreen.
    Post-session only. Never shown on live HUD.
    """
    session_id: str
    practitioner_id: str

    # The 4 core observations from Zone 3 LLM analysis
    signature_strength: str
    blind_spot: str
    instinct_ratio: str
    pressure_signature: str

    # Profile trend context (computed, not from LLM)
    session_count: int = 0
    profile_strengths: list[str] = field(default_factory=list)
    development_areas: list[str] = field(default_factory=list)
    override_success_rate: float = 50.0     # Shown as "Your instinct rate this session"
    missed_window_rate: float = 50.0         # Shown as "Windows missed this session"
    close_threshold_instinct: float = 50.0  # Shown as "You close at bar score X"

    # Metadata
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_fallback: bool = False

    def to_dict(self) -> dict:
        """Serializes for mobile app JSON response."""
        return {
            "session_id": self.session_id,
            "practitioner_id": self.practitioner_id,
            "observations": {
                "signature_strength": self.signature_strength,
                "blind_spot": self.blind_spot,
                "instinct_ratio": self.instinct_ratio,
                "pressure_signature": self.pressure_signature,
            },
            "profile_context": {
                "session_count": self.session_count,
                "strengths": self.profile_strengths,
                "development_areas": self.development_areas,
                "override_success_rate": self.override_success_rate,
                "missed_window_rate": self.missed_window_rate,
                "close_threshold_instinct": self.close_threshold_instinct,
            },
            "generated_at": self.generated_at.isoformat(),
            "is_fallback": self.is_fallback,
        }


class MirrorReportRenderer:
    """
    Composes the Mirror Report from Zone 3 analysis output + practitioner profile.

    Zone 3 only. NEVER called during Zone 2.
    Per PRD CLAUDE.md Critical Constraint #6:
      Mirror Report is post-session only. Hardcoded. Not configurable.
    """

    def render(
        self,
        analysis: SessionAnalysisResult,
        profile: Optional[PractitionerProfile],
    ) -> MirrorReportPayload:
        """
        Compose Mirror Report payload.
        Falls back gracefully if mirror_report or profile is None.
        Never raises.
        """
        # Ensure this is never called during Zone 2
        # (defensive check — actual enforcement is in the caller)
        logger.debug(
            "mirror_report.render",
            session_id=analysis.session_id,
            practitioner_id=profile.practitioner_id if profile else "unknown",
            note="POST-SESSION ONLY — never call from Zone 2",
        )

        mirror = analysis.mirror_report
        if mirror is None:
            return self._fallback_payload(analysis.session_id, profile)

        payload = MirrorReportPayload(
            session_id=analysis.session_id,
            practitioner_id=profile.practitioner_id if profile else "unknown",
            signature_strength=mirror.signature_strength,
            blind_spot=mirror.blind_spot,
            instinct_ratio=mirror.instinct_ratio,
            pressure_signature=mirror.pressure_signature,
            is_fallback=analysis.is_fallback,
        )

        # Add profile trend context if profile is available
        if profile is not None:
            payload.session_count = profile.session_count
            payload.profile_strengths = profile._identify_strengths()
            payload.development_areas = profile._identify_development_areas()
            payload.override_success_rate = profile.override_success_rate
            payload.missed_window_rate = profile.missed_window_rate
            payload.close_threshold_instinct = profile.close_threshold_instinct

        return payload

    def _fallback_payload(
        self,
        session_id: str,
        profile: Optional[PractitionerProfile],
    ) -> MirrorReportPayload:
        """Returns a fallback payload when LLM analysis was unavailable."""
        return MirrorReportPayload(
            session_id=session_id,
            practitioner_id=profile.practitioner_id if profile else "unknown",
            signature_strength="Session analysis was unavailable for this session.",
            blind_spot="Session analysis was unavailable for this session.",
            instinct_ratio="Session analysis was unavailable for this session.",
            pressure_signature="Session analysis was unavailable for this session.",
            session_count=profile.session_count if profile else 0,
            profile_strengths=profile._identify_strengths() if profile else [],
            development_areas=profile._identify_development_areas() if profile else [],
            is_fallback=True,
        )
