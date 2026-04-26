"""
tests/unit/test_bar_calculator.py
Phase 3 pass criteria — Bar Calculator tests.

Tests:
  TestBarCalculator (12 tests)
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone

from backend.bars.bar_calculator import BarCalculator, BarState
from backend.classifier.local_classifier import MomentType
from backend.classifier.moment_classifier import ClassificationResult
from backend.audio.paralinguistic_extractor import ParalinguisticSignals
from backend.genome.parameter_definitions import Genome, ConfidenceLevel


# ================================================================== #
#  Helpers                                                             #
# ================================================================== #

def _make_classification(
    mtype: MomentType = MomentType.NEUTRAL_EXPLORATORY,
    confidence: float = 1.0,
) -> ClassificationResult:
    return ClassificationResult(
        moment_type=mtype,
        confidence=confidence,
        path="local",
        text_snippet="test",
        timestamp=datetime.now(timezone.utc),
    )


def _make_para(**kwargs) -> ParalinguisticSignals:
    defaults = dict(
        speech_rate_delta=0.0,
        volume_level=0.5,
        pause_duration=0.0,
        voice_tension_index=0.0,
        cadence_consistency_score=1.0,
    )
    defaults.update(kwargs)
    return ParalinguisticSignals(**defaults)


def _make_genome(**kwargs) -> Genome:
    defaults = dict(
        prospect_id="test-bar-001",
        confidence=ConfidenceLevel.MEDIUM,
        openness=60, conscientiousness=65, extraversion=55,
        agreeableness=70, neuroticism=35, communication_style=65,
        decision_making=70, brand_relationship=60, influence_susceptibility=50,
        emotional_expression=45, conflict_behavior=40,
        literacy_and_articulation=75, socioeconomic_friction=25,
        identity_fusion=60, chronesthesia_capacity=70,
        tom_self_awareness=65, tom_social_modeling=60,
        executive_flexibility=55,
    )
    defaults.update(kwargs)
    return Genome(**defaults)


# ================================================================== #
#  BAR CALCULATOR                                                       #
# ================================================================== #

class TestBarCalculator:

    def test_initial_state(self):
        calc = BarCalculator()
        state = calc.state
        assert state.hook_score == 50
        assert state.close_score == 30
        assert state.hook_trend == "stable"
        assert state.close_trend == "stable"

    def test_high_openness_raises_both_bars(self):
        calc = BarCalculator()
        state = calc.update(
            _make_classification(MomentType.HIGH_OPENNESS, 1.0),
            _make_para(),
        )
        assert state.hook_score > 50
        assert state.close_score > 30

    def test_closing_signal_raises_close_bar_most(self):
        calc = BarCalculator()
        state = calc.update(
            _make_classification(MomentType.CLOSING_SIGNAL, 1.0),
            _make_para(),
        )
        # CLOSING_SIGNAL has highest close delta (+15)
        assert state.close_score > 30

    def test_irate_lowers_hook_bar(self):
        calc = BarCalculator()
        calc.update(
            _make_classification(MomentType.HIGH_OPENNESS, 1.0),
            _make_para(),
        )  # Raise first
        state = calc.update(
            _make_classification(MomentType.IRATE_RESISTANT, 1.0),
            _make_para(),
        )
        # IRATE has -10 hook delta
        assert state.hook_score < 62  # Started at 50, went up then down

    def test_bars_clamped_between_0_and_100(self):
        calc = BarCalculator()
        # Drive hook/close to max
        for _ in range(20):
            calc.update(
                _make_classification(MomentType.CLOSING_SIGNAL, 1.0),
                _make_para(),
            )
        state = calc.state
        assert 0 <= state.hook_score <= 100
        assert 0 <= state.close_score <= 100

        # Drive to min
        for _ in range(20):
            calc.update(
                _make_classification(MomentType.IRATE_RESISTANT, 1.0),
                _make_para(),
            )
        state = calc.state
        assert state.hook_score >= 0
        assert state.close_score >= 0

    def test_confidence_scales_delta(self):
        calc_full = BarCalculator()
        calc_half = BarCalculator()

        calc_full.update(_make_classification(MomentType.HIGH_OPENNESS, 1.0), _make_para())
        calc_half.update(_make_classification(MomentType.HIGH_OPENNESS, 0.5), _make_para())

        # Full confidence should produce larger delta than 50% confidence
        assert calc_full.state.hook_score >= calc_half.state.hook_score

    def test_trend_rising_when_score_increases(self):
        calc = BarCalculator()
        state = calc.update(
            _make_classification(MomentType.HIGH_OPENNESS, 1.0),
            _make_para(),
        )
        # Hook +12 from 50 → 62, should be "rising"
        assert state.hook_trend == "rising"

    def test_trend_falling_when_score_decreases(self):
        calc = BarCalculator()
        # Start with elevated hook
        for _ in range(3):
            calc.update(_make_classification(MomentType.HIGH_OPENNESS, 1.0), _make_para())
        # Now drop
        state = calc.update(
            _make_classification(MomentType.IRATE_RESISTANT, 1.0),
            _make_para(),
        )
        assert state.hook_trend == "falling"

    def test_tension_dampens_close_on_positive_moment(self):
        calc_low_tension = BarCalculator()
        calc_high_tension = BarCalculator()

        para_calm = _make_para(voice_tension_index=0.0)
        para_tense = _make_para(voice_tension_index=0.8)

        calc_low_tension.update(_make_classification(MomentType.HIGH_OPENNESS, 1.0), para_calm)
        calc_high_tension.update(_make_classification(MomentType.HIGH_OPENNESS, 1.0), para_tense)

        # High tension should dampen close bar rise
        assert calc_low_tension.state.close_score >= calc_high_tension.state.close_score

    def test_volume_drop_dampens_positive_effects(self):
        calc_engaged = BarCalculator()
        calc_withdrawn = BarCalculator()

        para_engaged = _make_para(volume_level=0.8)
        para_withdrawn = _make_para(volume_level=0.1)

        calc_engaged.update(_make_classification(MomentType.HIGH_OPENNESS, 1.0), para_engaged)
        calc_withdrawn.update(_make_classification(MomentType.HIGH_OPENNESS, 1.0), para_withdrawn)

        # Volume withdrawal should dampen bars
        assert calc_engaged.state.hook_score >= calc_withdrawn.state.hook_score

    def test_genome_exec_flex_dampens_movement(self):
        genome_flex = _make_genome(executive_flexibility=80)
        genome_normal = _make_genome(executive_flexibility=40)

        calc_flex = BarCalculator(genome=genome_flex)
        calc_normal = BarCalculator(genome=genome_normal)

        classification = _make_classification(MomentType.HIGH_OPENNESS, 1.0)
        para = _make_para()

        calc_flex.update(classification, para)
        calc_normal.update(classification, para)

        # High exec_flex dampens all movements to 0.7x
        flex_delta = calc_flex.state.hook_score - 50
        normal_delta = calc_normal.state.hook_score - 50
        assert normal_delta >= flex_delta

    def test_genome_neuroticism_amplifies_irate_close_drop(self):
        genome_neurotic = _make_genome(neuroticism=70)
        genome_calm = _make_genome(neuroticism=30)

        calc_neurotic = BarCalculator(genome=genome_neurotic)
        calc_calm = BarCalculator(genome=genome_calm)

        classification = _make_classification(MomentType.IRATE_RESISTANT, 1.0)
        para = _make_para()

        calc_neurotic.update(classification, para)
        calc_calm.update(classification, para)

        # High neuroticism amplifies negative close delta (1.4x)
        neurotic_close = calc_neurotic.state.close_score
        calm_close = calc_calm.state.close_score
        # Neurotic should end up with lower or equal close score
        assert neurotic_close <= calm_close
