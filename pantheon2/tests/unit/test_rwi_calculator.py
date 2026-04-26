"""
tests/unit/test_rwi_calculator.py + test_mutation_gate.py
Phase 1 pass criteria.
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone

from backend.rwi.rwi_calculator import RWICalculator
from backend.genome.parameter_definitions import (
    Genome, ConfidenceLevel, DeltaSignal, DeltaSignalType,
    MutationCandidate, MutationDecision, MutationStrength,
)
from backend.genome.genome_writer import validate_mutation_gate, apply_confirmed_mutation


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
#  RWI CALCULATOR TESTS                                               #
# ================================================================== #

class TestRWICalculator:

    def test_returns_rwi_snapshot(self):
        calc = RWICalculator()
        genome = _make_genome()
        rwi = calc.calculate(genome)

        assert 0 <= rwi.score <= 100
        assert rwi.window_status in ("closed", "narrowing", "open", "peak")
        assert rwi.prospect_id == "test-001"

    def test_high_friction_lowers_rwi(self):
        calc = RWICalculator()
        low_friction = _make_genome(socioeconomic_friction=10, neuroticism=20)
        high_friction = _make_genome(socioeconomic_friction=85, neuroticism=80)

        rwi_low = calc.calculate(low_friction)
        rwi_high = calc.calculate(high_friction)

        assert rwi_low.score > rwi_high.score

    def test_high_chronesthesia_raises_rwi(self):
        calc = RWICalculator()
        low_chron = _make_genome(chronesthesia_capacity=20, openness=20)
        high_chron = _make_genome(chronesthesia_capacity=90, openness=85)

        rwi_low = calc.calculate(low_chron)
        rwi_high = calc.calculate(high_chron)

        assert rwi_high.score > rwi_low.score

    def test_validation_delta_signal_raises_rwi(self):
        calc = RWICalculator()
        genome = _make_genome()
        baseline_rwi = calc.calculate(genome)

        validation_signal = DeltaSignal(
            prospect_id="test-001",
            signal_type=DeltaSignalType.VALIDATION_EVENT,
            source="linkedin",
            detected_at=datetime.now(timezone.utc),
            content_summary="Promoted to Senior VP",
            rwi_impact=15,
            display_message="Promotion post 2d ago → RWI +15",
        )

        boosted_rwi = calc.calculate(genome, delta_signals=[validation_signal])
        assert boosted_rwi.score > baseline_rwi.score

    def test_friction_delta_signal_lowers_rwi(self):
        calc = RWICalculator()
        genome = _make_genome()
        baseline_rwi = calc.calculate(genome)

        friction_signal = DeltaSignal(
            prospect_id="test-001",
            signal_type=DeltaSignalType.FRICTION_SIGNAL,
            source="linkedin",
            detected_at=datetime.now(timezone.utc),
            content_summary="Difficult quarter",
            rwi_impact=-12,
            display_message="Friction signal 3d ago → RWI -12",
        )

        reduced_rwi = calc.calculate(genome, delta_signals=[friction_signal])
        assert reduced_rwi.score < baseline_rwi.score

    def test_window_status_matches_score(self):
        calc = RWICalculator()
        # Force high RWI: very low friction, high chronesthesia
        peak_genome = _make_genome(
            socioeconomic_friction=5, neuroticism=5,
            chronesthesia_capacity=95, openness=90,
        )
        rwi = calc.calculate(peak_genome)
        if rwi.score >= 80:
            assert rwi.window_status == "peak"
        elif rwi.score >= 60:
            assert rwi.window_status == "open"


# ================================================================== #
#  MUTATION GATE TESTS                                                #
# ================================================================== #

class TestMutationGate:

    def _make_candidate(self, evidence_count: int = 3) -> MutationCandidate:
        return MutationCandidate(
            prospect_id="test-001",
            trait_name="openness",
            current_score=60,
            suggested_delta=8,
            suggested_new_score=68,
            evidence=[f"Observation {i}" for i in range(evidence_count)],
            strength=MutationStrength.STRONG,
        )

    def test_gate_approves_when_all_conditions_met(self):
        candidate = self._make_candidate(evidence_count=3)
        result = validate_mutation_gate(
            candidate=candidate,
            existing_log=[],
            has_cold_context_signal=True,
            observation_day_span=25,
            context_count=2,
        )
        assert result == MutationDecision.APPROVED

    def test_gate_rejects_insufficient_observations(self):
        candidate = self._make_candidate(evidence_count=2)  # Need 3+
        result = validate_mutation_gate(
            candidate=candidate,
            existing_log=[],
            has_cold_context_signal=True,
            observation_day_span=25,
            context_count=2,
        )
        assert result == MutationDecision.REJECTED_GATE

    def test_gate_rejects_insufficient_day_span(self):
        candidate = self._make_candidate(evidence_count=3)
        result = validate_mutation_gate(
            candidate=candidate,
            existing_log=[],
            has_cold_context_signal=True,
            observation_day_span=15,  # Need 21+
            context_count=2,
        )
        assert result == MutationDecision.REJECTED_GATE

    def test_gate_rejects_insufficient_contexts(self):
        candidate = self._make_candidate(evidence_count=3)
        result = validate_mutation_gate(
            candidate=candidate,
            existing_log=[],
            has_cold_context_signal=True,
            observation_day_span=25,
            context_count=1,  # Need 2+
        )
        assert result == MutationDecision.REJECTED_GATE

    def test_gate_rejects_no_cold_context_signal(self):
        candidate = self._make_candidate(evidence_count=3)
        result = validate_mutation_gate(
            candidate=candidate,
            existing_log=[],
            has_cold_context_signal=False,  # Required
            observation_day_span=25,
            context_count=2,
        )
        assert result == MutationDecision.REJECTED_GATE

    def test_gate_rejects_coherence_tension(self):
        candidate = self._make_candidate(evidence_count=3)
        candidate.is_coherence_tension = True
        result = validate_mutation_gate(
            candidate=candidate,
            existing_log=[],
            has_cold_context_signal=True,
            observation_day_span=25,
            context_count=2,
        )
        assert result == MutationDecision.REJECTED_COHERENCE

    def test_apply_mutation_clamps_to_100(self):
        genome = _make_genome(openness=98)
        candidate = MutationCandidate(
            prospect_id="test-001",
            trait_name="openness",
            current_score=98,
            suggested_delta=10,  # Would push to 108
            suggested_new_score=100,
            evidence=["e1", "e2", "e3"],
            strength=MutationStrength.STRONG,
        )
        updated_genome, log_entry = apply_confirmed_mutation(
            genome=genome,
            candidate=candidate,
            practitioner_id="p-001",
            observation_day_span=30,
            context_count=3,
            has_cold_context_signal=True,
        )
        assert updated_genome.openness == 100  # Clamped

    def test_apply_mutation_clamps_to_1(self):
        genome = _make_genome(openness=3)
        candidate = MutationCandidate(
            prospect_id="test-001",
            trait_name="openness",
            current_score=3,
            suggested_delta=-10,  # Would push below 1
            suggested_new_score=1,
            evidence=["e1", "e2", "e3"],
            strength=MutationStrength.STRONG,
        )
        updated_genome, _ = apply_confirmed_mutation(
            genome=genome,
            candidate=candidate,
            practitioner_id="p-001",
            observation_day_span=25,
            context_count=2,
            has_cold_context_signal=True,
        )
        assert updated_genome.openness == 1  # Clamped

    def test_apply_mutation_returns_log_entry(self):
        genome = _make_genome(openness=60)
        candidate = MutationCandidate(
            prospect_id="test-001",
            trait_name="openness",
            current_score=60,
            suggested_delta=8,
            suggested_new_score=68,
            evidence=["e1", "e2", "e3"],
            strength=MutationStrength.STRONG,
        )
        _, log_entry = apply_confirmed_mutation(
            genome=genome,
            candidate=candidate,
            practitioner_id="p-001",
            observation_day_span=25,
            context_count=2,
            has_cold_context_signal=True,
        )
        assert log_entry.trait_name == "openness"
        assert log_entry.old_score == 60
        assert log_entry.new_score == 68
        assert log_entry.delta == 8
        assert log_entry.confirmed_by == "p-001"
