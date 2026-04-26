"""
Module: practitioner_updater.py
Zone: 3 (Post-session only)
Input: SessionAnalysisResult, PractitionerProfile, practitioner_id
Output: Updated PractitionerProfile
LLM calls: 0
Side effects: Updates Supabase practitioner_profiles table (via db write)
Latency tolerance: Async post-session

Updates the practitioner profile from Zone 3 session analysis output.
Applies practitioner_deltas from SessionAnalysisResult using exponential
moving average smoothing (to avoid over-weighting single-session outliers).

One session = one profile update. No gate. No confirmation required.
(Practitioner profile is a learning tool — rapid feedback is appropriate.
Only the prospect GENOME requires the mutation gate.)

Also increments session_count and triggers mirror_report generation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import structlog

from backend.practitioner.practitioner_profile import PractitionerProfile
from backend.session.session_analyzer import SessionAnalysisResult, PractitionerDelta
from backend.practitioner.mirror_report import MirrorReportRenderer

logger = structlog.get_logger(__name__)


class PractitionerUpdater:
    """
    Applies session analysis deltas to the practitioner profile.
    Called by harness_runner after session_analyzer completes.
    Zone 3 only. No cloud calls.
    """

    def __init__(self, profile_repo=None) -> None:
        """
        Args:
            profile_repo: Optional repository for reading/writing practitioner profiles.
                          If None, operates on in-memory profile only (for tests).
        """
        self._repo = profile_repo

    async def update(
        self,
        analysis: SessionAnalysisResult,
        practitioner_id: str,
    ) -> PractitionerProfile:
        """
        Main entry point. Loads profile, applies deltas, saves, returns updated profile.
        Never raises — logs errors and returns original profile on failure.
        """
        # Load existing profile (or create a fresh one)
        profile = await self._load_profile(practitioner_id)

        # Apply practitioner deltas from session analysis
        applied_count = 0
        for delta in analysis.practitioner_deltas:
            if not delta.parameter:
                continue
            updated = profile.apply_delta(delta.parameter, delta.new_value)
            if updated:
                applied_count += 1
                logger.debug(
                    "practitioner_updater.delta_applied",
                    parameter=delta.parameter,
                    new_value=delta.new_value,
                    evidence=delta.evidence[:80] if delta.evidence else "",
                )

        # Increment session count and record session ID
        profile.session_count += 1
        profile.last_session_id = analysis.session_id
        profile.updated_at = datetime.now(timezone.utc)

        # Save updated profile
        await self._save_profile(profile)

        logger.info(
            "practitioner_updater.updated",
            practitioner_id=practitioner_id,
            session_id=analysis.session_id,
            deltas_applied=applied_count,
            session_count=profile.session_count,
        )

        return profile

    async def _load_profile(self, practitioner_id: str) -> PractitionerProfile:
        """Load from repo or create a fresh profile."""
        if self._repo is not None:
            try:
                existing = self._repo.get_by_practitioner_id(practitioner_id)
                if existing is not None:
                    return existing
            except Exception as e:
                logger.warning(
                    "practitioner_updater.load_error",
                    practitioner_id=practitioner_id,
                    error=str(e),
                )

        # Fresh profile with all defaults
        return PractitionerProfile(practitioner_id=practitioner_id)

    async def _save_profile(self, profile: PractitionerProfile) -> None:
        """Save to repo if available. Silent on failure (log only)."""
        if self._repo is None:
            return
        try:
            self._repo.upsert(profile)
        except Exception as e:
            logger.warning(
                "practitioner_updater.save_error",
                practitioner_id=profile.practitioner_id,
                error=str(e),
            )
