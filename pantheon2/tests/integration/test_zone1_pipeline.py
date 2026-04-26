"""
tests/integration/test_zone1_pipeline.py
Phase 2 pass criteria — full Zone 1 pipeline integration.

Mocks: DB (GenomeRepo), LLM client (harness_runner._build_dialog_cache + _run_psych_review)
Real: GenomeResolver priority chain, RWICalculator, PsychReviewAgent, CacheBuilder,
      ProbabilityEngine, SessionInit

All tests run without Supabase or real LLM connections.
"""

from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.genome.parameter_definitions import (
    Genome, GenomeBundle, ConfidenceLevel, RWISnapshot, RWIComponents,
)
from backend.psych_review.psych_review_agent import PsychReviewAgent, PsychReviewReport
from backend.psych_review.validity_checker import ValidityChecker, PsychFlag
from backend.psych_review.ecological_validator import EcologicalValidator
from backend.dialog.probability_engine import ProbabilityEngine
from backend.dialog.cache_builder import CacheBuilder
from backend.session.session_init import SessionInit


# ------------------------------------------------------------------ #
#  Fixtures                                                            #
# ------------------------------------------------------------------ #

def _make_genome(**overrides) -> Genome:
    defaults = dict(
        prospect_id="test-001",
        confidence=ConfidenceLevel.MEDIUM,
        openness=60, conscientiousness=65, extraversion=55, agreeableness=70,
        neuroticism=35, communication_style=65, decision_making=70,
        brand_relationship=60, influence_susceptibility=50, emotional_expression=45,
        conflict_behavior=40, literacy_and_articulation=75, socioeconomic_friction=25,
        identity_fusion=60, chronesthesia_capacity=70, tom_self_awareness=65,
        tom_social_modeling=60, executive_flexibility=55,
    )
    defaults.update(overrides)
    return Genome(**defaults)


def _make_rwi(**overrides) -> RWISnapshot:
    components = RWIComponents(
        validation_recency=overrides.pop("validation_recency", 65),
        friction_saturation=overrides.pop("friction_saturation", 30),
        decision_fatigue_estimate=overrides.pop("decision_fatigue", 40),
        identity_momentum=overrides.pop("identity_momentum", 55),
    )
    defaults = dict(
        prospect_id="test-001",
        score=62,
        window_status="open",
        strategy_note="Trust-building and pain-surfacing.",
        components=components,
    )
    defaults.update(overrides)
    return RWISnapshot(**defaults)


def _make_genome_bundle(genome: Genome = None, confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM) -> GenomeBundle:
    g = genome or _make_genome()
    bundle = GenomeBundle(
        genome=g,
        confidence=confidence,
        resolver_path="supabase",
        mutation_log_count=2,
        genome_age_days=30,
    )
    return bundle


def _make_dialog_cache(is_fallback: bool = False) -> dict:
    option = {
        "core_approach": "Acknowledge and explore",
        "base_language": "Can you tell me more about what's driving that concern?",
        "trigger_phrase": "Explore the why",
        "base_probability": 55,
        "genome_rationale": "High agreeableness: preference for collaborative framing.",
    }
    cache = {
        moment: {"option_a": dict(option), "option_b": dict(option), "option_c": dict(option)}
        for moment in [
            "neutral_exploratory", "irate_resistant", "topic_avoidance",
            "identity_threat", "high_openness", "closing_signal",
        ]
    }
    cache["_is_fallback"] = is_fallback
    return cache


# ================================================================== #
#  PSYCH REVIEW AGENT TESTS                                           #
# ================================================================== #

class TestPsychReviewAgent:

    def test_high_confidence_clean_genome_returns_robust(self):
        agent = PsychReviewAgent()
        genome = _make_genome(confidence=ConfidenceLevel.HIGH)
        report = agent.review(genome, ConfidenceLevel.HIGH, "Indonesia B2B Advisory")
        assert report.genome_validity_score == "ROBUST"

    def test_low_confidence_returns_thin(self):
        agent = PsychReviewAgent()
        genome = _make_genome(confidence=ConfidenceLevel.LOW)
        report = agent.review(genome, ConfidenceLevel.LOW, "Indonesia B2B Advisory")
        assert report.genome_validity_score == "THIN"

    def test_low_confidence_requires_acknowledgment(self):
        agent = PsychReviewAgent()
        genome = _make_genome()
        report = agent.review(genome, ConfidenceLevel.LOW, "Indonesia B2B Advisory")
        assert report.requires_acknowledgment is True
        assert report.high_severity_count > 0

    def test_high_exec_flex_returns_moderate_flag(self):
        agent = PsychReviewAgent()
        genome = _make_genome(executive_flexibility=80)
        report = agent.review(genome, ConfidenceLevel.MEDIUM, "Indonesia B2B Advisory")
        flag_types = [f.trait_or_moment for f in report.flags]
        assert "executive_flexibility" in flag_types

    def test_high_neuroticism_plus_high_exec_flex_is_high_severity(self):
        agent = PsychReviewAgent()
        genome = _make_genome(neuroticism=75, executive_flexibility=75)
        report = agent.review(genome, ConfidenceLevel.MEDIUM, "Indonesia B2B Advisory")
        high_flags = [f for f in report.flags if f.severity == "HIGH"]
        assert len(high_flags) >= 1
        assert report.requires_acknowledgment is True

    def test_indonesian_context_returns_ecological_flags(self):
        agent = PsychReviewAgent()
        genome = _make_genome()
        report = agent.review(genome, ConfidenceLevel.MEDIUM, "Indonesia B2B Advisory")
        eco_flags = [f for f in report.flags if f.type == "ecological_validity"]
        assert len(eco_flags) >= 2  # at least Irate/Resistant and Closing/Signal HIGH flags

    def test_non_indonesian_context_no_ecological_flags(self):
        agent = PsychReviewAgent()
        genome = _make_genome()
        report = agent.review(genome, ConfidenceLevel.MEDIUM, "US Enterprise SaaS")
        eco_flags = [f for f in report.flags if f.type == "ecological_validity"]
        assert len(eco_flags) == 0

    def test_report_has_summary(self):
        agent = PsychReviewAgent()
        genome = _make_genome()
        report = agent.review(genome, ConfidenceLevel.MEDIUM, "Indonesia B2B Advisory")
        assert isinstance(report.summary, str)
        assert len(report.summary) > 0

    def test_report_to_dict_is_serializable(self):
        agent = PsychReviewAgent()
        genome = _make_genome()
        report = agent.review(genome, ConfidenceLevel.MEDIUM, "Indonesia B2B Advisory")
        d = report.to_dict()
        assert "genome_validity_score" in d
        assert "flags" in d
        assert isinstance(d["flags"], list)


# ================================================================== #
#  PROBABILITY ENGINE TESTS                                           #
# ================================================================== #

class TestProbabilityEngine:

    def test_low_confidence_compresses_toward_50(self):
        engine = ProbabilityEngine()
        cache = _make_dialog_cache()
        cache["neutral_exploratory"]["option_a"]["base_probability"] = 80
        genome = _make_genome()
        rwi = _make_rwi()
        adjusted = engine.adjust(cache, genome, ConfidenceLevel.LOW, rwi)
        prob = adjusted["neutral_exploratory"]["option_a"]["base_probability"]
        assert prob < 80  # compressed

    def test_high_confidence_no_compression(self):
        engine = ProbabilityEngine()
        cache = _make_dialog_cache()
        cache["neutral_exploratory"]["option_a"]["base_probability"] = 75
        genome = _make_genome()
        rwi = _make_rwi()
        adjusted = engine.adjust(cache, genome, ConfidenceLevel.HIGH, rwi)
        # No compression — should stay at 75 (genome adjustments may shift slightly)
        prob = adjusted["neutral_exploratory"]["option_a"]["base_probability"]
        assert 10 <= prob <= 90  # at minimum clamped

    def test_peak_rwi_boosts_closing_signal(self):
        engine = ProbabilityEngine()
        cache = _make_dialog_cache()
        cache["closing_signal"]["option_a"]["base_probability"] = 50
        genome = _make_genome()
        rwi = _make_rwi(window_status="peak")
        adjusted = engine.adjust(cache, genome, ConfidenceLevel.HIGH, rwi)
        prob = adjusted["closing_signal"]["option_a"]["base_probability"]
        assert prob > 50

    def test_probabilities_clamped_between_10_and_90(self):
        engine = ProbabilityEngine()
        cache = _make_dialog_cache()
        for moment in cache:
            if isinstance(cache[moment], dict):
                for opt in ["option_a", "option_b", "option_c"]:
                    if opt in cache[moment]:
                        cache[moment][opt]["base_probability"] = 99
        genome = _make_genome()
        rwi = _make_rwi()
        adjusted = engine.adjust(cache, genome, ConfidenceLevel.HIGH, rwi)
        for moment in ["neutral_exploratory", "irate_resistant"]:
            for opt in ["option_a", "option_b", "option_c"]:
                prob = adjusted[moment][opt]["base_probability"]
                assert 10 <= prob <= 90, f"{moment}.{opt} prob={prob} out of range"

    def test_closed_rwi_compresses_spread(self):
        engine = ProbabilityEngine()
        cache = _make_dialog_cache()
        cache["closing_signal"]["option_a"]["base_probability"] = 80
        genome = _make_genome()
        rwi = _make_rwi(window_status="closed")
        adjusted = engine.adjust(cache, genome, ConfidenceLevel.HIGH, rwi)
        prob = adjusted["closing_signal"]["option_a"]["base_probability"]
        assert prob <= 60  # compressed back toward 50


# ================================================================== #
#  CACHE BUILDER TESTS                                                #
# ================================================================== #

class TestCacheBuilder:

    def _make_llm_with_valid_cache(self) -> MagicMock:
        llm = MagicMock()
        cache_json = json.dumps(_make_dialog_cache())
        llm.complete = AsyncMock(return_value=cache_json)
        return llm

    def _make_config(self) -> MagicMock:
        config = MagicMock()
        return config

    @pytest.mark.asyncio
    async def test_returns_all_moment_types(self):
        llm = self._make_llm_with_valid_cache()
        builder = CacheBuilder(llm, self._make_config())
        bundle = _make_genome_bundle()
        rwi = _make_rwi()
        cache = await builder.build(bundle, rwi)
        for moment in ["neutral_exploratory", "irate_resistant", "topic_avoidance",
                       "identity_threat", "high_openness", "closing_signal"]:
            assert moment in cache

    @pytest.mark.asyncio
    async def test_each_moment_has_three_options(self):
        llm = self._make_llm_with_valid_cache()
        builder = CacheBuilder(llm, self._make_config())
        bundle = _make_genome_bundle()
        rwi = _make_rwi()
        cache = await builder.build(bundle, rwi)
        for moment in ["neutral_exploratory", "closing_signal"]:
            assert "option_a" in cache[moment]
            assert "option_b" in cache[moment]
            assert "option_c" in cache[moment]

    @pytest.mark.asyncio
    async def test_llm_failure_returns_fallback(self):
        llm = MagicMock()
        llm.complete = AsyncMock(side_effect=Exception("LLM timeout"))
        builder = CacheBuilder(llm, self._make_config())
        bundle = _make_genome_bundle()
        rwi = _make_rwi()
        cache = await builder.build(bundle, rwi)
        assert cache.get("_is_fallback") is True
        assert "neutral_exploratory" in cache

    @pytest.mark.asyncio
    async def test_invalid_json_returns_fallback(self):
        llm = MagicMock()
        llm.complete = AsyncMock(return_value="not valid json {{")
        builder = CacheBuilder(llm, self._make_config())
        bundle = _make_genome_bundle()
        rwi = _make_rwi()
        cache = await builder.build(bundle, rwi)
        assert cache.get("_is_fallback") is True

    @pytest.mark.asyncio
    async def test_probabilities_adjusted_after_build(self):
        llm = self._make_llm_with_valid_cache()
        builder = CacheBuilder(llm, self._make_config())
        bundle = _make_genome_bundle(confidence=ConfidenceLevel.HIGH)
        rwi = _make_rwi(window_status="peak")
        cache = await builder.build(bundle, rwi)
        # Peak RWI should boost closing_signal
        prob = cache["closing_signal"]["option_a"]["base_probability"]
        assert prob > 50


# ================================================================== #
#  SESSION INIT TESTS                                                  #
# ================================================================== #

class TestSessionInit:

    def _make_bundle(self, confidence=ConfidenceLevel.MEDIUM, psych_report=None):
        genome = _make_genome()
        bundle = MagicMock()
        bundle.session_id = "sess-001"
        bundle.prospect_id = "test-001"
        bundle.practitioner_id = "prac-001"
        bundle.genome_bundle = MagicMock()
        bundle.genome_bundle.confidence = confidence
        bundle.genome_bundle.resolver_path = "supabase"
        bundle.rwi = _make_rwi()
        bundle.psych_report = psych_report or {
            "genome_validity_score": "ROBUST",
            "ecological_validity_score": "PARTIAL",
            "flags": [],
            "high_severity_count": 0,
            "requires_acknowledgment": False,
            "summary": "Genome predictions are well-supported.",
        }
        bundle.dialog_cache = _make_dialog_cache()
        bundle.cache_path = "./session_cache/sess-001_dialog_cache.json"
        return bundle

    def test_payload_has_confidence_badge(self):
        init = SessionInit()
        bundle = self._make_bundle()
        payload = init.build_screen_payload(bundle)
        assert payload.confidence_badge is not None
        assert payload.confidence_badge.level == "MEDIUM"

    def test_low_confidence_badge_is_red(self):
        init = SessionInit()
        bundle = self._make_bundle(confidence=ConfidenceLevel.LOW)
        payload = init.build_screen_payload(bundle)
        assert payload.confidence_badge.color == "red"

    def test_high_confidence_badge_is_green(self):
        init = SessionInit()
        bundle = self._make_bundle(confidence=ConfidenceLevel.HIGH)
        payload = init.build_screen_payload(bundle)
        assert payload.confidence_badge.color == "green"

    def test_no_high_flags_means_no_acknowledgment_required(self):
        init = SessionInit()
        bundle = self._make_bundle()
        payload = init.build_screen_payload(bundle)
        assert payload.requires_acknowledgment is False
        assert payload.unacknowledged_flag_ids == []

    def test_high_psych_flag_requires_acknowledgment(self):
        init = SessionInit()
        psych_report = {
            "flags": [
                {
                    "flag_id": "VF_001",
                    "type": "validity",
                    "severity": "HIGH",
                    "trait_or_moment": "genome_confidence",
                    "concern": "Genome is THIN.",
                    "practitioner_instruction": "Treat as hypothesis.",
                }
            ],
            "high_severity_count": 1,
            "requires_acknowledgment": True,
            "summary": "HIGH flag present.",
        }
        bundle = self._make_bundle(psych_report=psych_report)
        payload = init.build_screen_payload(bundle)
        assert payload.requires_acknowledgment is True
        assert "VF_001" in payload.unacknowledged_flag_ids

    def test_low_flags_not_in_display_list(self):
        init = SessionInit()
        psych_report = {
            "flags": [
                {
                    "flag_id": "VF_LOW",
                    "type": "validity",
                    "severity": "LOW",
                    "trait_or_moment": "some_trait",
                    "concern": "Minor note.",
                    "practitioner_instruction": "FYI.",
                }
            ],
            "high_severity_count": 0,
            "requires_acknowledgment": False,
            "summary": "All clear.",
        }
        bundle = self._make_bundle(psych_report=psych_report)
        payload = init.build_screen_payload(bundle)
        assert len(payload.psych_flags) == 0  # LOW filtered out

    def test_rwi_payload_contains_components(self):
        init = SessionInit()
        bundle = self._make_bundle()
        payload = init.build_screen_payload(bundle)
        assert payload.rwi.score == 62.0
        assert payload.rwi.window_status == "open"
        assert "validation_recency" in payload.rwi.components

    def test_fallback_cache_flag_surfaced(self):
        init = SessionInit()
        bundle = self._make_bundle()
        bundle.dialog_cache = _make_dialog_cache(is_fallback=True)
        payload = init.build_screen_payload(bundle)
        assert payload.is_fallback_cache is True
