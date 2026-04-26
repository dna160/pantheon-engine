"""
Module: psych_review_agent.py
Zone: 1 (Pre-session — runs after genome_resolver, before cache_builder)
Input: Genome, ConfidenceLevel, market_context (str)
Output: PsychReviewReport
LLM calls: 0 (rule-based only; LLM overlay is handled by harness_runner._run_psych_review)
Side effects: None
Latency tolerance: <200ms

Orchestrates ValidityChecker + EcologicalValidator → PsychReviewReport.
The harness_runner runs the LLM over the same genome and merges results into
the report dict it returns to the session bundle.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import structlog

from backend.genome.parameter_definitions import Genome, ConfidenceLevel
from backend.psych_review.validity_checker import ValidityChecker, PsychFlag
from backend.psych_review.ecological_validator import EcologicalValidator

logger = structlog.get_logger(__name__)


@dataclass
class PsychReviewReport:
    genome_validity_score: str         # "ROBUST" | "PARTIAL" | "THIN"
    ecological_validity_score: str     # "COMPATIBLE" | "PARTIAL" | "INCOMPATIBLE"
    flags: list[PsychFlag] = field(default_factory=list)
    high_severity_count: int = 0
    requires_acknowledgment: bool = False
    overall_confidence_adjustment: str = "none"   # "none" | "compress_5pts" | "compress_15pts"
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "genome_validity_score": self.genome_validity_score,
            "ecological_validity_score": self.ecological_validity_score,
            "flags": [
                {
                    "flag_id": f.flag_id,
                    "type": f.type,
                    "severity": f.severity,
                    "trait_or_moment": f.trait_or_moment,
                    "concern": f.concern,
                    "practitioner_instruction": f.practitioner_instruction,
                }
                for f in self.flags
            ],
            "high_severity_count": self.high_severity_count,
            "requires_acknowledgment": self.requires_acknowledgment,
            "overall_confidence_adjustment": self.overall_confidence_adjustment,
            "summary": self.summary,
        }


class PsychReviewAgent:
    """
    Orchestrates rule-based psychological validity review.
    Called from Zone 1 (session_init / harness_runner) before cache build.
    """

    def __init__(self) -> None:
        self._validity = ValidityChecker()
        self._ecological = EcologicalValidator()

    def review(
        self,
        genome: Genome,
        confidence: ConfidenceLevel,
        market_context: str = "Indonesia B2B Advisory",
    ) -> PsychReviewReport:
        """
        Runs rule-based validity + ecological checks.
        Returns PsychReviewReport with all flags classified by severity.
        """
        validity_flags = self._validity.check(genome, confidence)
        ecological_flags = self._ecological.check(genome, market_context)
        all_flags = validity_flags + ecological_flags

        high_count = sum(1 for f in all_flags if f.severity == "HIGH")
        moderate_count = sum(1 for f in all_flags if f.severity == "MODERATE")

        genome_validity = self._score_genome_validity(validity_flags, confidence)
        ecological_validity = self._score_ecological_validity(ecological_flags)
        confidence_adjustment = self._compute_confidence_adjustment(confidence, high_count)

        summary = self._build_summary(
            genome_validity, ecological_validity, high_count, moderate_count, confidence
        )

        report = PsychReviewReport(
            genome_validity_score=genome_validity,
            ecological_validity_score=ecological_validity,
            flags=all_flags,
            high_severity_count=high_count,
            requires_acknowledgment=high_count > 0,
            overall_confidence_adjustment=confidence_adjustment,
            summary=summary,
        )

        logger.info(
            "psych_review.complete",
            validity=genome_validity,
            ecological=ecological_validity,
            high_flags=high_count,
            moderate_flags=moderate_count,
            requires_acknowledgment=report.requires_acknowledgment,
        )

        return report

    def _score_genome_validity(
        self, validity_flags: list[PsychFlag], confidence: ConfidenceLevel
    ) -> str:
        if confidence == ConfidenceLevel.LOW:
            return "THIN"
        high_validity_flags = [f for f in validity_flags if f.severity == "HIGH"]
        if high_validity_flags:
            return "THIN"
        moderate_flags = [f for f in validity_flags if f.severity == "MODERATE"]
        if moderate_flags:
            return "PARTIAL"
        return "ROBUST"

    def _score_ecological_validity(self, ecological_flags: list[PsychFlag]) -> str:
        if not ecological_flags:
            return "COMPATIBLE"
        high_eco = [f for f in ecological_flags if f.severity == "HIGH"]
        if high_eco:
            return "INCOMPATIBLE"
        return "PARTIAL"

    def _compute_confidence_adjustment(
        self, confidence: ConfidenceLevel, high_count: int
    ) -> str:
        if confidence == ConfidenceLevel.LOW:
            return "compress_15pts"
        if confidence == ConfidenceLevel.MEDIUM and high_count > 0:
            return "compress_5pts"
        return "none"

    def _build_summary(
        self,
        genome_validity: str,
        ecological_validity: str,
        high_count: int,
        moderate_count: int,
        confidence: ConfidenceLevel,
    ) -> str:
        parts = []

        if genome_validity == "ROBUST" and ecological_validity == "COMPATIBLE":
            parts.append("Genome predictions are well-supported and ecologically calibrated.")
        elif genome_validity == "THIN":
            parts.append(
                "Genome confidence is LOW — treat all dialog options as starting hypotheses."
            )
        else:
            parts.append(
                f"Genome validity: {genome_validity}. Ecological fit: {ecological_validity}."
            )

        if high_count > 0:
            parts.append(
                f"{high_count} HIGH-severity flag(s) require acknowledgment before session start."
            )
        elif moderate_count > 0:
            parts.append(
                f"{moderate_count} MODERATE flag(s) — review before proceeding."
            )
        else:
            parts.append("No critical flags detected.")

        return " ".join(parts)
