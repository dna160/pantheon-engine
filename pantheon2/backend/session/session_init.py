"""
Module: session_init.py
Zone: 1 (Pre-session — final step before Zone 2 starts)
Input: SessionBundle (from harness_runner.prepare_session)
Output: PreSessionScreenPayload (structured data for mobile PreSessionScreen)
LLM calls: 0
Side effects: None (read-only — display only)
Latency tolerance: <100ms (pure data assembly)

Assembles the pre-session screen payload from the SessionBundle.
The mobile app (PreSessionScreen.tsx) renders this data.

Critical constraints:
- ConfidenceBadge MUST appear in payload (never omitted)
- HIGH severity psych flags MUST be in requires_acknowledgment list
- GO button is blocked until all HIGH flags are acknowledged
- Mirror Report is never included here (post-session only)
"""

from __future__ import annotations

from dataclasses import dataclass, field

import structlog

from backend.genome.parameter_definitions import ConfidenceLevel

logger = structlog.get_logger(__name__)


@dataclass
class ConfidenceBadgePayload:
    level: str           # "HIGH" | "MEDIUM" | "LOW"
    label: str           # Human-readable label
    color: str           # "green" | "yellow" | "red"  (renamed from color_hint; never "amber")


@dataclass
class RWIPayload:
    score: float
    window_status: str   # "peak" | "open" | "narrowing" | "closed"
    components: dict


@dataclass
class PsychFlagDisplay:
    flag_id: str
    severity: str
    flag_type: str              # renamed from trait_or_moment
    message: str                # renamed from concern
    recommendation: str         # renamed from practitioner_instruction
    requires_acknowledgment: bool


@dataclass
class PreSessionScreenPayload:
    session_id: str
    prospect_id: str
    practitioner_id: str

    # Always present — ConfidenceBadge constraint
    confidence_badge: ConfidenceBadgePayload

    # RWI summary
    rwi: RWIPayload

    # Psych review — summary always shown; flags filtered to MODERATE+
    psych_summary: str
    psych_flags: list[PsychFlagDisplay] = field(default_factory=list)

    # GO gating
    requires_acknowledgment: bool = False
    unacknowledged_flag_ids: list[str] = field(default_factory=list)

    # Cache metadata
    cache_path: str = ""
    is_fallback_cache: bool = False

    # Genome resolver path (for practitioner awareness)
    genome_resolver_path: str = ""


class SessionInit:
    """
    Assembles the pre-session screen payload from a SessionBundle.
    Called after harness_runner.prepare_session() completes.
    """

    def build_screen_payload(self, bundle) -> PreSessionScreenPayload:
        """
        bundle: SessionBundle from harness_runner.
        Returns PreSessionScreenPayload for mobile PreSessionScreen.
        """
        confidence_badge = self._build_confidence_badge(bundle.genome_bundle.confidence)
        rwi_payload = self._build_rwi_payload(bundle.rwi)
        psych_flags, unacknowledged = self._build_psych_flags(bundle.psych_report)
        psych_summary = self._extract_psych_summary(bundle.psych_report)
        is_fallback = bundle.dialog_cache.get("_is_fallback", False)

        resolver_path = getattr(bundle.genome_bundle, "resolver_path", "unknown")

        payload = PreSessionScreenPayload(
            session_id=bundle.session_id,
            prospect_id=bundle.prospect_id,
            practitioner_id=bundle.practitioner_id,
            confidence_badge=confidence_badge,
            rwi=rwi_payload,
            psych_summary=psych_summary,
            psych_flags=psych_flags,
            requires_acknowledgment=len(unacknowledged) > 0,
            unacknowledged_flag_ids=unacknowledged,
            cache_path=bundle.cache_path,
            is_fallback_cache=is_fallback,
            genome_resolver_path=resolver_path,
        )

        logger.info(
            "session_init.payload_built",
            session_id=bundle.session_id,
            confidence=bundle.genome_bundle.confidence.value,
            rwi_score=bundle.rwi.score,
            requires_acknowledgment=payload.requires_acknowledgment,
            flag_count=len(psych_flags),
        )

        return payload

    def _build_confidence_badge(self, confidence: ConfidenceLevel) -> ConfidenceBadgePayload:
        if confidence == ConfidenceLevel.HIGH:
            return ConfidenceBadgePayload(level="HIGH", label="High Confidence", color="green")
        if confidence == ConfidenceLevel.MEDIUM:
            return ConfidenceBadgePayload(level="MEDIUM", label="Medium Confidence", color="yellow")
        return ConfidenceBadgePayload(level="LOW", label="Low Confidence — Use as Hypothesis", color="red")

    def _build_rwi_payload(self, rwi) -> RWIPayload:
        components = rwi.components
        return RWIPayload(
            score=rwi.score,
            window_status=rwi.window_status,
            components={
                "validation_recency": components.validation_recency,
                "friction_saturation": components.friction_saturation,
                "decision_fatigue": components.decision_fatigue_estimate,
                "identity_momentum": components.identity_momentum,
            },
        )

    def _build_psych_flags(
        self, psych_report: dict
    ) -> tuple[list[PsychFlagDisplay], list[str]]:
        """
        Filters to MODERATE+ flags for display.
        Returns (display_flags, unacknowledged_high_flag_ids).
        """
        flags = psych_report.get("flags", []) if isinstance(psych_report, dict) else []
        display_flags = []
        unacknowledged = []

        for f in flags:
            severity = f.get("severity", "LOW") if isinstance(f, dict) else getattr(f, "severity", "LOW")
            if severity == "LOW":
                continue  # LOW flags available in "Full Review" only, not shown by default

            flag_id = f.get("flag_id", "") if isinstance(f, dict) else getattr(f, "flag_id", "")
            is_high = severity == "HIGH"

            display_flags.append(PsychFlagDisplay(
                flag_id=flag_id,
                severity=severity,
                flag_type=(
                    f.get("flag_type", f.get("trait_or_moment", ""))
                    if isinstance(f, dict)
                    else getattr(f, "flag_type", getattr(f, "trait_or_moment", ""))
                ),
                message=(
                    f.get("message", f.get("concern", ""))
                    if isinstance(f, dict)
                    else getattr(f, "message", getattr(f, "concern", ""))
                ),
                recommendation=(
                    f.get("recommendation", f.get("practitioner_instruction", ""))
                    if isinstance(f, dict)
                    else getattr(f, "recommendation", getattr(f, "practitioner_instruction", ""))
                ),
                requires_acknowledgment=is_high,
            ))
            if is_high:
                unacknowledged.append(flag_id)

        return display_flags, unacknowledged

    def _extract_psych_summary(self, psych_report: dict) -> str:
        if isinstance(psych_report, dict):
            return psych_report.get("summary", "Adversarial review complete.")
        return "Adversarial review complete."
