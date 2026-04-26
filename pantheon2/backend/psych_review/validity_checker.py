"""
Module: validity_checker.py
Zone: 1 (Pre-session — runs before cache_builder)
Input: Genome, ConfidenceLevel
Output: list[PsychFlag] — validity concerns only
LLM calls: 0
Side effects: None
Latency tolerance: <100ms (pure rule-based)

Rule-based validity checks. No LLM. Flags known weak predictions from the
validity table in adversarial-psychologist/SKILL.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from backend.genome.parameter_definitions import Genome, ConfidenceLevel


@dataclass
class PsychFlag:
    flag_id: str
    type: str                    # "validity" | "ecological_validity"
    severity: str                # "LOW" | "MODERATE" | "HIGH"
    trait_or_moment: str
    concern: str
    practitioner_instruction: str


_TRAIT_VALIDITY = {
    "tom_social_modeling": {
        "severity": "MODERATE",
        "concern": (
            "High tom_social_modeling score predicts the prospect will detect inauthentic tactics. "
            "However, inauthenticity detection research (Bond & DePaulo 2006) shows humans perform "
            "near-chance on lie detection. Do not assume the prospect is a reliable authenticator."
        ),
        "practitioner_instruction": (
            "Be genuinely consultative regardless of this score. The risk is not detection — it is "
            "that formulaic tactics erode trust over multiple sessions even if not caught immediately."
        ),
    },
    "neuroticism": {
        "severity": "MODERATE",
        "concern": (
            "High neuroticism predicts shutdown under urgency. However, shutdown vs. freeze vs. "
            "exit are not distinguishable from audio alone. Behavioral response under stress is "
            "highly individual and context-dependent."
        ),
        "practitioner_instruction": (
            "Watch for physical cues (longer pauses, quieter voice) rather than relying on this "
            "prediction. If you detect tension, slow down rather than escalating."
        ),
    },
}


class ValidityChecker:
    """
    Rule-based validity checker. Flags known weak predictions based on
    the adversarial-psychologist validity table. No LLM calls.
    """

    def check(self, genome: Genome, confidence: ConfidenceLevel) -> list[PsychFlag]:
        flags: list[PsychFlag] = []
        flag_counter = 1

        # --- Check 1: executive_flexibility > 70 → all surface-behavior predictions unreliable ---
        if genome.executive_flexibility is not None and genome.executive_flexibility > 70:
            flags.append(PsychFlag(
                flag_id=f"VF_{flag_counter:03d}",
                type="validity",
                severity="MODERATE",
                trait_or_moment="executive_flexibility",
                concern=(
                    f"executive_flexibility={genome.executive_flexibility} (>70). High self-monitoring "
                    "capacity means surface behavior (affect, language tone, pacing) may not reflect "
                    "internal state. Leary (1995) and Baumeister (2002) confirm high self-monitors "
                    "actively manage performed vs. experienced emotion."
                ),
                practitioner_instruction=(
                    "Treat all surface-behavior predictions as potentially unreliable for this prospect. "
                    "Weight paralinguistic divergence signals more heavily — look for micro-inconsistencies "
                    "between verbal and tonal cues."
                ),
            ))
            flag_counter += 1

        # --- Check 2: neuroticism HIGH + executive_flexibility HIGH — most dangerous false-positive ---
        if (
            genome.neuroticism is not None and genome.neuroticism > 65
            and genome.executive_flexibility is not None and genome.executive_flexibility > 65
        ):
            flags.append(PsychFlag(
                flag_id=f"VF_{flag_counter:03d}",
                type="validity",
                severity="HIGH",
                trait_or_moment="neuroticism+executive_flexibility",
                concern=(
                    f"neuroticism={genome.neuroticism} AND executive_flexibility={genome.executive_flexibility} "
                    "both elevated. This is the most dangerous false-positive profile: the prospect appears "
                    "calm and composed externally (high self-monitor) while experiencing significant internal "
                    "anxiety (high neuroticism). Surface signals will actively mislead."
                ),
                practitioner_instruction=(
                    "Do not read surface composure as genuine comfort. Slow the pace and create explicit "
                    "permission to express concerns. Watch for over-qualified agreement (yes-but patterns), "
                    "topic deflection, and increased formality as stress markers."
                ),
            ))
            flag_counter += 1

        # --- Check 3: tom_social_modeling > 70 —  inauthenticity detector concern ---
        if genome.tom_social_modeling is not None and genome.tom_social_modeling > 70:
            entry = _TRAIT_VALIDITY["tom_social_modeling"]
            flags.append(PsychFlag(
                flag_id=f"VF_{flag_counter:03d}",
                type="validity",
                severity=entry["severity"],
                trait_or_moment="tom_social_modeling",
                concern=entry["concern"],
                practitioner_instruction=entry["practitioner_instruction"],
            ))
            flag_counter += 1

        # --- Check 4: neuroticism > 70 — shutdown prediction is PARTIAL ---
        if genome.neuroticism is not None and genome.neuroticism > 70:
            entry = _TRAIT_VALIDITY["neuroticism"]
            flags.append(PsychFlag(
                flag_id=f"VF_{flag_counter:03d}",
                type="validity",
                severity=entry["severity"],
                trait_or_moment="neuroticism",
                concern=entry["concern"],
                practitioner_instruction=entry["practitioner_instruction"],
            ))
            flag_counter += 1

        # --- Check 5: LOW confidence → genome is THIN ---
        if confidence == ConfidenceLevel.LOW:
            flags.append(PsychFlag(
                flag_id=f"VF_{flag_counter:03d}",
                type="validity",
                severity="HIGH",
                trait_or_moment="genome_confidence",
                concern=(
                    "Genome confidence is LOW. All 18 parameter scores are at or near default (50). "
                    "Predictions are based on insufficient signal. Per Fleeson (2001), behavioral traits "
                    "are density distributions — single-session inferences are unreliable baselines."
                ),
                practitioner_instruction=(
                    "Treat all genome-derived dialog options as starting hypotheses, not calibrated "
                    "recommendations. Pay close attention to live signals and update your mental model "
                    "continuously during the session."
                ),
            ))
            flag_counter += 1

        # --- Check 6: scrape-derived genome — social media caution ---
        if confidence == ConfidenceLevel.MEDIUM and genome.last_scraped_at is not None:
            flags.append(PsychFlag(
                flag_id=f"VF_{flag_counter:03d}",
                type="validity",
                severity="MODERATE",
                trait_or_moment="scrape_source",
                concern=(
                    "Genome derived from LinkedIn/Instagram data. Vazire (2010) establishes that "
                    "performed self-presentation on social platforms ≠ private behavior. Professional "
                    "profiles are managed impressions, not behavioral ground truth."
                ),
                practitioner_instruction=(
                    "Weight social media signals as aspirational self-concept rather than behavioral "
                    "baseline. Verify key trait inferences in the first 5 minutes of conversation."
                ),
            ))

        return flags
