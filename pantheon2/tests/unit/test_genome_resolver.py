"""
tests/unit/test_genome_resolver.py
Phase 1 pass criteria — resolver priority chain + confidence scoring.

These tests mock the database and scrape layers so no Supabase connection is required.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.genome.parameter_definitions import Genome, GenomeBundle, ConfidenceLevel
from backend.genome.confidence_scorer import score_confidence, apply_low_confidence_penalty
from backend.genome.genome_builder import GenomeBuilder


def _make_genome(**overrides) -> Genome:
    defaults = dict(
        prospect_id="test-001", confidence=ConfidenceLevel.MEDIUM,
        openness=60, conscientiousness=65, extraversion=55, agreeableness=70,
        neuroticism=35, communication_style=65, decision_making=70,
        brand_relationship=60, influence_susceptibility=50, emotional_expression=45,
        conflict_behavior=40, literacy_and_articulation=75, socioeconomic_friction=25,
        identity_fusion=60, chronesthesia_capacity=70, tom_self_awareness=65,
        tom_social_modeling=60, executive_flexibility=55,
    )
    defaults.update(overrides)
    return Genome(**defaults)


# ================================================================== #
#  CONFIDENCE SCORER TESTS                                            #
# ================================================================== #

class TestConfidenceScorer:

    def test_supabase_fresh_with_mutations_is_high(self):
        result = score_confidence(
            resolver_path="supabase",
            mutation_log_count=2,
            genome_age_days=30,
        )
        assert result == ConfidenceLevel.HIGH

    def test_supabase_stale_is_medium(self):
        result = score_confidence(
            resolver_path="supabase",
            mutation_log_count=2,
            genome_age_days=100,  # > 90 days
        )
        assert result == ConfidenceLevel.MEDIUM

    def test_supabase_no_mutations_is_medium(self):
        result = score_confidence(
            resolver_path="supabase",
            mutation_log_count=0,
            genome_age_days=30,
        )
        assert result == ConfidenceLevel.MEDIUM

    def test_fresh_scrape_is_medium(self):
        result = score_confidence(
            resolver_path="fresh_scrape",
            mutation_log_count=0,
            genome_age_days=None,
        )
        assert result == ConfidenceLevel.MEDIUM

    def test_intake_form_is_low(self):
        result = score_confidence(
            resolver_path="intake_form",
            mutation_log_count=0,
            genome_age_days=None,
        )
        assert result == ConfidenceLevel.LOW


# ================================================================== #
#  LOW CONFIDENCE PENALTY TESTS                                       #
# ================================================================== #

class TestLowConfidencePenalty:

    def test_scores_above_50_compressed_down(self):
        scores = {"openness": 80, "neuroticism": 70}
        result = apply_low_confidence_penalty(scores)
        assert result["openness"] < 80
        assert result["neuroticism"] < 70

    def test_scores_below_50_compressed_up(self):
        scores = {"openness": 20, "neuroticism": 30}
        result = apply_low_confidence_penalty(scores)
        assert result["openness"] > 20
        assert result["neuroticism"] > 30

    def test_score_at_50_unchanged(self):
        scores = {"openness": 50}
        result = apply_low_confidence_penalty(scores)
        assert result["openness"] == 50

    def test_compression_is_exactly_15_points(self):
        scores = {"openness": 75}
        result = apply_low_confidence_penalty(scores)
        assert result["openness"] == 60  # 75 - 15

    def test_compression_does_not_cross_50(self):
        scores = {"openness": 58}
        result = apply_low_confidence_penalty(scores)
        assert result["openness"] == 50  # clipped at 50, not 43


# ================================================================== #
#  GENOME BUILDER TESTS                                               #
# ================================================================== #

class TestGenomeBuilder:

    def test_build_from_intake_all_neutral(self):
        builder = GenomeBuilder()
        genome = builder.build_from_intake(
            prospect_id="test-001",
            intake_answers={},  # All defaults = 50
        )
        assert genome.prospect_id == "test-001"
        assert genome.confidence == ConfidenceLevel.LOW
        assert genome.openness == 50

    def test_build_from_intake_custom_answers(self):
        builder = GenomeBuilder()
        genome = builder.build_from_intake(
            prospect_id="test-002",
            intake_answers={
                "receptiveness_to_new_ideas": 85,
                "stress_sensitivity": 20,
            },
        )
        assert genome.openness == 85
        assert genome.neuroticism == 20

    def test_build_from_intake_clamped_to_100(self):
        builder = GenomeBuilder()
        genome = builder.build_from_intake(
            prospect_id="test-003",
            intake_answers={"receptiveness_to_new_ideas": 120},  # Over 100
        )
        assert genome.openness == 100

    def test_build_from_intake_clamped_to_1(self):
        builder = GenomeBuilder()
        genome = builder.build_from_intake(
            prospect_id="test-004",
            intake_answers={"receptiveness_to_new_ideas": -10},  # Under 1
        )
        assert genome.openness == 1

    def test_build_from_scrape_returns_genome(self):
        builder = GenomeBuilder()
        genome = builder.build_from_scrape(
            prospect_id="test-005",
            signals={"extracted_signals": {
                "experimental_language_count": 5,
                "friction_signals_count": 8,
            }},
        )
        assert genome.prospect_id == "test-005"
        assert genome.confidence == ConfidenceLevel.MEDIUM
        assert 1 <= genome.openness <= 100
        assert 1 <= genome.socioeconomic_friction <= 100


# ================================================================== #
#  GENOME RESOLVER TESTS (mocked DB + scrape)                         #
# ================================================================== #

class TestGenomeResolverPriorityChain:

    def _make_resolver(self):
        """Build a GenomeResolver with a mocked Supabase client so no real connection is needed."""
        from backend.genome.genome_resolver import GenomeResolver
        with patch("backend.db.supabase_client.get_supabase_client", return_value=MagicMock()):
            return GenomeResolver()

    @pytest.mark.asyncio
    async def test_priority1_supabase_hit(self):
        """When Supabase has a fresh genome with mutations, use it."""
        resolver = self._make_resolver()
        mock_genome = _make_genome()

        with patch.object(resolver._db, "get_by_prospect_id", return_value=mock_genome), \
             patch.object(resolver._db, "genome_age_days", return_value=30), \
             patch.object(resolver._db, "get_mutation_log", return_value=["entry1"]):

            bundle = await resolver.resolve("test-001")
            assert bundle.resolver_path == "supabase"
            assert bundle.confidence == ConfidenceLevel.HIGH

    @pytest.mark.asyncio
    async def test_priority2_scrape_when_no_supabase(self):
        """When no Supabase genome exists, falls back to scrape."""
        resolver = self._make_resolver()
        mock_scraped = _make_genome(confidence=ConfidenceLevel.MEDIUM)

        with patch.object(resolver._db, "get_by_prospect_id", return_value=None), \
             patch.object(resolver._db, "genome_age_days", return_value=None), \
             patch.object(resolver._db, "get_mutation_log", return_value=[]), \
             patch.object(resolver._db, "upsert_genome", return_value=None), \
             patch.object(resolver, "_run_scrape", new=AsyncMock(return_value=mock_scraped)):

            bundle = await resolver.resolve("test-002")
            assert bundle.resolver_path == "fresh_scrape"
            assert bundle.confidence == ConfidenceLevel.MEDIUM

    @pytest.mark.asyncio
    async def test_priority3_intake_when_scrape_fails(self):
        """When scrape fails, falls back to intake form (neutral genome)."""
        resolver = self._make_resolver()

        with patch.object(resolver._db, "get_by_prospect_id", return_value=None), \
             patch.object(resolver._db, "genome_age_days", return_value=None), \
             patch.object(resolver._db, "get_mutation_log", return_value=[]), \
             patch.object(resolver, "_run_scrape", new=AsyncMock(side_effect=Exception("Network error"))):

            bundle = await resolver.resolve("test-003")
            assert bundle.resolver_path == "intake_form"
            assert bundle.confidence == ConfidenceLevel.LOW
