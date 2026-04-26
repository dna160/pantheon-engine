"""
Module: genome_builder.py
Zone: 1 (Pre-session — called by genome_resolver when scrape or intake path is taken)
Input: raw_signals dict (from scrape_pipeline or intake form answers)
Output: Genome
LLM calls: 0 (rule-based derivation only)
Side effects: None
Latency tolerance: <500ms

Derives all 18 genome parameters from behavioral signal evidence.
Rules are deterministic — no randomness, no LLM inference at this layer.
Optionally imports v1 genome_culture for cultural modifiers if available.
"""

from __future__ import annotations

import os
import sys
from typing import Any
import structlog

from backend.genome.parameter_definitions import Genome, ConfidenceLevel

logger = structlog.get_logger(__name__)

# ------------------------------------------------------------------ #
#  Optional v1 integration: cultural genome modifiers                 #
# ------------------------------------------------------------------ #

_V1_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)
_HAS_V1_CULTURE = False
try:
    if os.path.exists(os.path.join(_V1_PATH, "genome_culture.py")):
        sys.path.insert(0, _V1_PATH)
        from genome_culture import apply_cultural_modifiers  # type: ignore
        _HAS_V1_CULTURE = True
        logger.info("genome_builder.v1_culture.loaded")
except Exception:
    pass


def _clamp(val: int) -> int:
    return max(1, min(100, val))


class GenomeBuilder:
    """
    Builds a Genome from raw scrape signals or intake form answers.
    All 18 parameters are derived from behavioral evidence only.
    """

    def build_from_scrape(
        self,
        prospect_id: str,
        signals: dict[str, Any],
        confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM,
    ) -> Genome:
        """
        Builds genome from social scrape signals.
        signals keys: linkedin_posts, instagram_posts, extracted_signals (from signal_extractor)
        """
        extracted = signals.get("extracted_signals", {})
        scores = self._derive_scores(extracted, source="scrape")
        return self._assemble_genome(prospect_id, scores, confidence)

    def build_from_intake(
        self,
        prospect_id: str,
        intake_answers: dict[str, Any],
        confidence: ConfidenceLevel = ConfidenceLevel.LOW,
    ) -> Genome:
        """
        Builds genome from manual intake form answers (12-question rapid intake).
        Scores are compressed by confidence_scorer when confidence=LOW.
        """
        scores = self._derive_scores_from_intake(intake_answers)
        return self._assemble_genome(prospect_id, scores, confidence)

    # ------------------------------------------------------------------ #
    #  Score derivation — scrape path                                      #
    # ------------------------------------------------------------------ #

    def _derive_scores(self, signals: dict[str, Any], source: str) -> dict[str, int]:
        """
        Rule-based derivation of all 18 genome parameters from extracted signals.
        Returns a dict of trait_name → INT 1–100.
        """
        s = signals  # shorthand

        # --- Cluster A: OCEAN-derived ---
        openness = _clamp(
            50
            + int(s.get("experimental_language_count", 0) * 4)
            - int(s.get("conservative_language_count", 0) * 3)
        )
        conscientiousness = _clamp(
            50
            + int(s.get("planning_language_count", 0) * 5)
            + int(s.get("achievement_posts_count", 0) * 2)
        )
        extraversion = _clamp(
            50
            + int(s.get("public_posts_per_month", 0) * 2)
            + int(s.get("engagement_rate", 0.0) * 20)
        )
        agreeableness = _clamp(
            50
            + int(s.get("collaborative_language_count", 0) * 3)
            - int(s.get("confrontational_language_count", 0) * 4)
        )
        neuroticism = _clamp(
            50
            + int(s.get("anxiety_language_count", 0) * 5)
            - int(s.get("stability_language_count", 0) * 3)
        )

        # --- Cluster B: Behavioral and Cultural ---
        communication_style = _clamp(
            50
            + int(s.get("direct_language_count", 0) * 4)
            - int(s.get("indirect_language_count", 0) * 3)
        )
        decision_making = _clamp(
            50
            + int(s.get("data_references_count", 0) * 5)
            - int(s.get("narrative_language_count", 0) * 2)
        )
        brand_relationship = _clamp(
            50
            + int(s.get("brand_mentions_count", 0) * 3)
            - int(s.get("price_focus_count", 0) * 4)
        )
        influence_susceptibility = _clamp(
            50
            + int(s.get("social_proof_references", 0) * 4)
            + int(s.get("peer_validation_posts", 0) * 3)
        )
        emotional_expression = _clamp(
            50
            + int(s.get("emotional_posts_count", 0) * 4)
            - int(s.get("stoic_language_count", 0) * 3)
        )
        conflict_behavior = _clamp(
            50
            + int(s.get("confrontational_language_count", 0) * 4)
            - int(s.get("avoidance_language_count", 0) * 3)
        )
        literacy_and_articulation = _clamp(
            50
            + int(s.get("vocabulary_complexity_score", 0) * 5)
            + int(s.get("formal_writing_count", 0) * 2)
        )
        socioeconomic_friction = _clamp(
            50
            + int(s.get("friction_signals_count", 0) * 6)
            - int(s.get("success_signals_count", 0) * 3)
        )

        # --- Cluster C: Cognitive Architecture ---
        identity_fusion = _clamp(
            50
            + int(s.get("group_identity_language_count", 0) * 5)
            - int(s.get("individualist_language_count", 0) * 3)
        )
        chronesthesia_capacity = _clamp(
            50
            + int(s.get("future_vision_posts", 0) * 5)
            + int(s.get("long_term_planning_language", 0) * 3)
        )
        tom_self_awareness = _clamp(
            50
            + int(s.get("self_reflection_posts", 0) * 4)
            + int(s.get("meta_commentary_count", 0) * 3)
        )
        tom_social_modeling = _clamp(
            50
            + int(s.get("other_perspective_language", 0) * 4)
            + int(s.get("audience_awareness_signals", 0) * 3)
        )
        executive_flexibility = _clamp(
            50
            + int(s.get("professional_persona_signals", 0) * 4)
            - int(s.get("authentic_vulnerability_posts", 0) * 3)
        )

        return {
            "openness": openness,
            "conscientiousness": conscientiousness,
            "extraversion": extraversion,
            "agreeableness": agreeableness,
            "neuroticism": neuroticism,
            "communication_style": communication_style,
            "decision_making": decision_making,
            "brand_relationship": brand_relationship,
            "influence_susceptibility": influence_susceptibility,
            "emotional_expression": emotional_expression,
            "conflict_behavior": conflict_behavior,
            "literacy_and_articulation": literacy_and_articulation,
            "socioeconomic_friction": socioeconomic_friction,
            "identity_fusion": identity_fusion,
            "chronesthesia_capacity": chronesthesia_capacity,
            "tom_self_awareness": tom_self_awareness,
            "tom_social_modeling": tom_social_modeling,
            "executive_flexibility": executive_flexibility,
        }

    # ------------------------------------------------------------------ #
    #  Score derivation — intake form path                                 #
    # ------------------------------------------------------------------ #

    def _derive_scores_from_intake(self, answers: dict[str, Any]) -> dict[str, int]:
        """
        Derives genome scores from 12-question intake form answers.
        Questions map directly to parameter clusters.
        All scores default to 50 (neutral) when evidence is absent.
        """
        scores: dict[str, int] = {
            "openness": int(answers.get("receptiveness_to_new_ideas", 50)),
            "conscientiousness": int(answers.get("planning_orientation", 50)),
            "extraversion": int(answers.get("social_energy", 50)),
            "agreeableness": int(answers.get("cooperation_tendency", 50)),
            "neuroticism": int(answers.get("stress_sensitivity", 50)),
            "communication_style": int(answers.get("communication_directness", 50)),
            "decision_making": int(answers.get("evidence_vs_intuition", 50)),
            "brand_relationship": int(answers.get("brand_loyalty", 50)),
            "influence_susceptibility": int(answers.get("social_proof_sensitivity", 50)),
            "emotional_expression": int(answers.get("emotional_openness", 50)),
            "conflict_behavior": int(answers.get("conflict_engagement", 50)),
            "literacy_and_articulation": int(answers.get("communication_sophistication", 50)),
            "socioeconomic_friction": int(answers.get("systemic_pressure_level", 50)),
            "identity_fusion": int(answers.get("group_identity_strength", 50)),
            "chronesthesia_capacity": int(answers.get("future_orientation", 50)),
            "tom_self_awareness": int(answers.get("self_awareness_level", 50)),
            "tom_social_modeling": int(answers.get("social_reading_ability", 50)),
            "executive_flexibility": int(answers.get("professional_persona_gap", 50)),
        }
        return {k: _clamp(v) for k, v in scores.items()}

    # ------------------------------------------------------------------ #
    #  Assemble                                                            #
    # ------------------------------------------------------------------ #

    def _assemble_genome(
        self,
        prospect_id: str,
        scores: dict[str, int],
        confidence: ConfidenceLevel,
    ) -> Genome:
        """Builds a Genome model from derived scores. Optionally applies v1 cultural modifiers."""
        if _HAS_V1_CULTURE:
            try:
                scores = apply_cultural_modifiers(scores)  # type: ignore
                logger.info("genome_builder.v1_culture.applied", prospect_id=prospect_id)
            except Exception as e:
                logger.warning("genome_builder.v1_culture.failed", error=str(e))

        return Genome(
            prospect_id=prospect_id,
            confidence=confidence,
            **scores,
        )
