"""
Module: practitioner_profile.py
Zone: 3 (Post-session — updated after analysis)
Input: PractitionerDelta list from session_analyzer
Output: PractitionerProfile (10 parameters, accumulated across sessions)
LLM calls: 0
Side effects: None (practitioner_updater writes to Supabase)
Latency tolerance: N/A (post-session, async)

10-parameter practitioner self-profile.
These parameters describe HOW the practitioner performs — their behavioral
patterns under different moment types, their instincts, their blind spots.

Unlike the prospect genome (18 traits, mutation-gated), practitioner parameters
accumulate across every session without a velocity gate. The practitioner is
explicitly being trained — rapid feedback is appropriate.

Parameters derived from session_analyzer.py output (zone3_session_analyzer prompt):
  1. close_threshold_instinct     — avg Close bar at actual close attempt moments
  2. missed_window_rate           — % closing_signal moments without advance option
  3. silence_tolerance            — avg wait time before filling silence (seconds)
  4. override_success_rate        — % deviations from top-probability that were net positive
  5. hook_instinct                — avg Hook bar delta in first 5 classified moments
  6. resilience_under_resistance  — avg Hook/Close maintenance during IRATE/IDENTITY_THREAT
  7. rapport_approach             — avg option diversity in NEUTRAL_EXPLORATORY moments
  8. preparation_depth            — correlation: genome predictions vs. actual moment patterns
  9. adaptive_range               — option diversity score (breadth vs. always same option)
 10. pressure_signature_score     — avg bar drop during high-pressure moments (inverse = better)

All values float 0.0–100.0 (rates use 0–100 not 0.0–1.0 for UI consistency).
session_count tracks total sessions accumulated (used for trend lines in mobile app).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field

import structlog

logger = structlog.get_logger(__name__)


class PractitionerProfile(BaseModel):
    """
    10-parameter practitioner behavioral profile.
    Accumulated from session_analyzer output across all sessions.
    Updated by practitioner_updater.py after every session.
    Stored in Supabase practitioner_profiles table.
    """

    practitioner_id: str

    # ------------------------------------------------------------------ #
    #  Core instinct parameters                                            #
    # ------------------------------------------------------------------ #

    close_threshold_instinct: float = Field(
        50.0, ge=0.0, le=100.0,
        description=(
            "Average Close bar value at actual close attempt moments. "
            "High = attempts close when prospect is ready. "
            "Low = premature closing attempts or missed windows entirely."
        )
    )

    missed_window_rate: float = Field(
        50.0, ge=0.0, le=100.0,
        description=(
            "% of closing_signal moments where no advance option was chosen. "
            "High = frequently lets closing windows pass. "
            "Low = consistent window capture."
        )
    )

    silence_tolerance: float = Field(
        2.0, ge=0.0, le=30.0,
        description=(
            "Average seconds practitioner waits after speaking before filling silence. "
            "Calibrates patience under high-stakes pauses. "
            "Measured in seconds (0–30 scale for display)."
        )
    )

    override_success_rate: float = Field(
        50.0, ge=0.0, le=100.0,
        description=(
            "% of deviations from top-probability option that produced net positive "
            "Hook/Close bar delta. High = practitioner's instincts beat the model. "
            "Low = model trust would have served better."
        )
    )

    # ------------------------------------------------------------------ #
    #  Behavioral signature parameters                                     #
    # ------------------------------------------------------------------ #

    hook_instinct: float = Field(
        50.0, ge=0.0, le=100.0,
        description=(
            "Average Hook bar delta in first 5 classified moments of session. "
            "High = practitioner consistently activates attention early. "
            "Low = early session engagement is a recurring weakness."
        )
    )

    resilience_under_resistance: float = Field(
        50.0, ge=0.0, le=100.0,
        description=(
            "Average Hook/Close bar maintenance ratio during IRATE_RESISTANT "
            "and IDENTITY_THREAT moments. High = holds ground under pressure. "
            "Low = bars collapse when prospect pushes back."
        )
    )

    rapport_approach: float = Field(
        50.0, ge=0.0, le=100.0,
        description=(
            "Option selection diversity in NEUTRAL_EXPLORATORY moments. "
            "High = adapts approach per prospect. "
            "Low = relies on same opener regardless of prospect profile."
        )
    )

    preparation_depth: float = Field(
        50.0, ge=0.0, le=100.0,
        description=(
            "Correlation between genome predictions and actual moment patterns. "
            "High = practitioner reads sessions consistent with genome model. "
            "Low = session diverges from expected pattern — may indicate "
            "prep shortfall or genome accuracy gap."
        )
    )

    adaptive_range: float = Field(
        50.0, ge=0.0, le=100.0,
        description=(
            "Option diversity score across the session. "
            "High = draws from all 3 options as context demands. "
            "Low = locked onto one option type regardless of moment."
        )
    )

    pressure_signature_score: float = Field(
        50.0, ge=0.0, le=100.0,
        description=(
            "Average bar preservation under high-pressure moments "
            "(IRATE + IDENTITY_THREAT combined). "
            "100 = no bar drop under pressure. 0 = severe collapse. "
            "Inverse of pressure_drop_rate for UI display."
        )
    )

    # ------------------------------------------------------------------ #
    #  Meta                                                                #
    # ------------------------------------------------------------------ #

    session_count: int = Field(
        0, ge=0,
        description="Total sessions accumulated into this profile."
    )

    last_session_id: Optional[str] = None

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    model_config = {"from_attributes": True}

    def apply_delta(self, parameter: str, new_value: float) -> bool:
        """
        Apply a single parameter update from session analysis.
        Returns True if parameter exists and was updated.
        Uses exponential moving average (alpha=0.3) to smooth session-to-session noise.
        """
        if not hasattr(self, parameter):
            logger.warning(
                "practitioner_profile.unknown_parameter",
                parameter=parameter,
            )
            return False

        current = getattr(self, parameter)
        # Exponential moving average: smooth updates across sessions
        # alpha = 0.3 → new session has 30% weight, history has 70%
        alpha = 0.3
        smoothed = current * (1 - alpha) + new_value * alpha
        setattr(self, parameter, round(smoothed, 2))
        return True

    @property
    def summary(self) -> dict:
        """Returns a display-ready summary for the Mirror Report screen."""
        return {
            "practitioner_id": self.practitioner_id,
            "session_count": self.session_count,
            "strengths": self._identify_strengths(),
            "development_areas": self._identify_development_areas(),
        }

    def _identify_strengths(self) -> list[str]:
        """Parameters scoring > 65 are strengths."""
        strengths = []
        parameter_labels = {
            "close_threshold_instinct": "Closing instinct",
            "override_success_rate": "Instinct vs. model",
            "hook_instinct": "Opening engagement",
            "resilience_under_resistance": "Pressure resilience",
            "adaptive_range": "Option adaptability",
            "preparation_depth": "Session preparation",
            "pressure_signature_score": "High-pressure composure",
        }
        for param, label in parameter_labels.items():
            if getattr(self, param, 0) > 65:
                strengths.append(label)
        return strengths

    def _identify_development_areas(self) -> list[str]:
        """Parameters scoring < 40 are development areas."""
        areas = []
        parameter_labels = {
            "missed_window_rate": "Window capture",
            "silence_tolerance": "Silence tolerance",
            "rapport_approach": "Rapport adaptability",
            "hook_instinct": "Opening engagement",
            "resilience_under_resistance": "Pressure resilience",
            "override_success_rate": "Instinct calibration",
        }
        for param, label in parameter_labels.items():
            val = getattr(self, param, 50.0)
            # missed_window_rate: high = bad, so invert
            if param == "missed_window_rate":
                if val > 60:
                    areas.append(label)
            elif val < 40:
                areas.append(label)
        return areas
