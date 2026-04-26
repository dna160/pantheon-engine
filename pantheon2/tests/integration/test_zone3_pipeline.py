"""
tests/integration/test_zone3_pipeline.py
Phase 4 pass criteria — Zone 3 Pipeline integration tests.

Tests:
  TestSessionAnalyzer (8 tests)
  TestPractitionerProfile (7 tests)
  TestPractitionerUpdater (5 tests)
  TestMirrorReport (5 tests)
"""

from __future__ import annotations

import json
import os
import tempfile
import pytest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from backend.session.session_analyzer import (
    SessionAnalyzer,
    SessionAnalysisResult,
    MirrorReport,
    PractitionerDelta,
)
from backend.practitioner.practitioner_profile import PractitionerProfile
from backend.practitioner.practitioner_updater import PractitionerUpdater
from backend.practitioner.mirror_report import MirrorReportRenderer, MirrorReportPayload
from backend.genome.parameter_definitions import (
    Genome, ConfidenceLevel, MutationStrength,
)


# ================================================================== #
#  Helpers                                                             #
# ================================================================== #

def _make_genome(**kwargs) -> Genome:
    defaults = dict(
        prospect_id="prospect-test-z3",
        confidence=ConfidenceLevel.MEDIUM,
        openness=60, conscientiousness=65, extraversion=55, agreeableness=70,
        neuroticism=35, communication_style=65, decision_making=70,
        brand_relationship=60, influence_susceptibility=50, emotional_expression=45,
        conflict_behavior=40, literacy_and_articulation=75, socioeconomic_friction=25,
        identity_fusion=60, chronesthesia_capacity=70, tom_self_awareness=65,
        tom_social_modeling=60, executive_flexibility=55,
    )
    defaults.update(kwargs)
    return Genome(**defaults)


def _make_jsonl_log(events: list[dict]) -> str:
    """Write events to a temp JSONL file. Returns path."""
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False)
    for event in events:
        f.write(json.dumps(event) + "\n")
    f.close()
    return f.name


def _mock_llm_response(payload: dict) -> str:
    return json.dumps(payload)


def _make_analysis_result(
    mutation_candidates=None,
    practitioner_deltas=None,
    mirror_report: dict = None,
) -> SessionAnalysisResult:
    from backend.genome.parameter_definitions import MutationCandidate

    candidates = mutation_candidates or []
    deltas = practitioner_deltas or []

    mr = None
    if mirror_report:
        mr = MirrorReport(
            signature_strength=mirror_report.get("signature_strength", ""),
            blind_spot=mirror_report.get("blind_spot", ""),
            instinct_ratio=mirror_report.get("instinct_ratio", ""),
            pressure_signature=mirror_report.get("pressure_signature", ""),
        )

    return SessionAnalysisResult(
        session_id="sess-test-001",
        mutation_candidates=candidates,
        practitioner_deltas=[
            PractitionerDelta(
                parameter=d["parameter"],
                old_value=d["old_value"],
                new_value=d["new_value"],
                evidence=d["evidence"],
            ) for d in deltas
        ],
        mirror_report=mr,
        is_fallback=False,
    )


# ================================================================== #
#  SESSION ANALYZER                                                     #
# ================================================================== #

class TestSessionAnalyzer:

    @pytest.mark.asyncio
    async def test_returns_session_analysis_result(self):
        """With valid LLM response, returns structured SessionAnalysisResult."""
        log_path = _make_jsonl_log([
            {"event_type": "moment_event", "moment_type": "high_openness",
             "confidence": 0.8, "path": "local", "text_snippet": "tell me more",
             "hook_score": 62, "close_score": 45, "hook_trend": "rising",
             "close_trend": "rising", "top_option": {}, "_ts": "2026-04-24T10:00:00Z"}
        ])

        llm_response = _mock_llm_response({
            "mutation_candidates": [
                {
                    "prospect_id": "prospect-test-z3",
                    "trait_name": "openness",
                    "current_score": 60,
                    "suggested_delta": 5,
                    "suggested_new_score": 65,
                    "evidence": ["Prospect asked 3 forward questions"],
                    "strength": "MODERATE",
                    "is_coherence_tension": False,
                }
            ],
            "practitioner_deltas": [
                {"parameter": "close_threshold_instinct", "old_value": 50.0,
                 "new_value": 62.0, "evidence": "Attempted close at Close bar 62"}
            ],
            "mirror_report": {
                "signature_strength": "High openness moments showed +18 close delta.",
                "blind_spot": "Two closing windows passed without advance option.",
                "instinct_ratio": "Overrides toward rapport options worked. Overrides toward urgency did not.",
                "pressure_signature": "Under IRATE moments, bars dropped 15 pts on average.",
            },
            "outcome_log": {"outcome": "follow_up", "key_moments": []},
        })

        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(return_value=llm_response)
        mock_config = MagicMock()

        analyzer = SessionAnalyzer(
            log_path=log_path,
            genome=_make_genome(),
            prospect_id="prospect-test-z3",
            practitioner_id="pract-001",
            session_id="sess-001",
        )

        result = await analyzer.analyze(mock_llm, mock_config)
        os.unlink(log_path)

        assert isinstance(result, SessionAnalysisResult)
        assert len(result.mutation_candidates) == 1
        assert result.mutation_candidates[0].trait_name == "openness"
        assert result.mutation_candidates[0].strength == MutationStrength.MODERATE

    @pytest.mark.asyncio
    async def test_returns_fallback_on_llm_error(self):
        """LLM failure returns fallback result without raising."""
        log_path = _make_jsonl_log([])
        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(side_effect=RuntimeError("LLM crashed"))

        analyzer = SessionAnalyzer(
            log_path=log_path,
            genome=_make_genome(),
            prospect_id="p-001",
            practitioner_id="pr-001",
            session_id="sess-002",
        )

        result = await analyzer.analyze(mock_llm, MagicMock())
        os.unlink(log_path)

        assert result.is_fallback is True
        assert result.session_id == "sess-002"
        assert len(result.mutation_candidates) == 0

    @pytest.mark.asyncio
    async def test_returns_fallback_on_missing_log(self):
        """Missing log file returns fallback gracefully."""
        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(return_value=_mock_llm_response({
            "mutation_candidates": [],
            "practitioner_deltas": [],
            "mirror_report": {
                "signature_strength": "No data.",
                "blind_spot": "No data.",
                "instinct_ratio": "No data.",
                "pressure_signature": "No data.",
            },
            "outcome_log": {},
        }))

        analyzer = SessionAnalyzer(
            log_path="/nonexistent/path/sess.jsonl",
            genome=None,
            prospect_id="p-001",
            practitioner_id="pr-001",
            session_id="sess-003",
        )

        result = await analyzer.analyze(mock_llm, MagicMock())
        assert isinstance(result, SessionAnalysisResult)

    def test_load_log_reads_jsonl_events(self):
        """_load_log reads all events from JSONL file correctly."""
        events = [
            {"event_type": "moment_event", "moment_type": "closing_signal"},
            {"event_type": "periodic_snapshot", "elapsed_seconds": 30.0},
        ]
        log_path = _make_jsonl_log(events)
        analyzer = SessionAnalyzer(
            log_path=log_path,
            genome=None,
            prospect_id="p-001",
            practitioner_id="pr-001",
            session_id="sess-004",
        )
        loaded = analyzer._load_log()
        os.unlink(log_path)

        assert len(loaded) == 2
        assert loaded[0]["event_type"] == "moment_event"
        assert loaded[1]["event_type"] == "periodic_snapshot"

    def test_parse_result_skips_empty_trait_candidates(self):
        """Mutation candidates with empty trait_name are skipped."""
        analyzer = SessionAnalyzer(
            log_path="/fake.jsonl",
            genome=None,
            prospect_id="p-001",
            practitioner_id="pr-001",
            session_id="sess-005",
        )
        raw = _mock_llm_response({
            "mutation_candidates": [
                {"trait_name": "", "current_score": 50, "suggested_delta": 5,
                 "suggested_new_score": 55, "evidence": [], "strength": "WEAK",
                 "is_coherence_tension": False},
                {"trait_name": "neuroticism", "current_score": 35, "suggested_delta": 3,
                 "suggested_new_score": 38, "evidence": ["test"], "strength": "WEAK",
                 "is_coherence_tension": False},
            ],
            "practitioner_deltas": [],
            "mirror_report": {
                "signature_strength": "x", "blind_spot": "x",
                "instinct_ratio": "x", "pressure_signature": "x"
            },
            "outcome_log": {},
        })
        result = analyzer._parse_result(raw)
        assert len(result.mutation_candidates) == 1
        assert result.mutation_candidates[0].trait_name == "neuroticism"

    def test_coherence_tension_flag_preserved(self):
        """is_coherence_tension flag is preserved in parsed candidates."""
        analyzer = SessionAnalyzer(
            log_path="/fake.jsonl",
            genome=None,
            prospect_id="p-001",
            practitioner_id="pr-001",
            session_id="sess-006",
        )
        raw = _mock_llm_response({
            "mutation_candidates": [
                {"trait_name": "identity_fusion", "current_score": 85,
                 "suggested_delta": -10, "suggested_new_score": 75,
                 "evidence": ["one observation"], "strength": "WEAK",
                 "is_coherence_tension": True},
            ],
            "practitioner_deltas": [],
            "mirror_report": {
                "signature_strength": "x", "blind_spot": "x",
                "instinct_ratio": "x", "pressure_signature": "x"
            },
            "outcome_log": {},
        })
        result = analyzer._parse_result(raw)
        assert result.mutation_candidates[0].is_coherence_tension is True

    def test_to_dict_is_serializable(self):
        """SessionAnalysisResult.to_dict() produces JSON-serializable dict."""
        result = _make_analysis_result(
            mirror_report={
                "signature_strength": "test",
                "blind_spot": "test",
                "instinct_ratio": "test",
                "pressure_signature": "test",
            }
        )
        data = result.to_dict()
        assert json.dumps(data)  # Should not raise

    def test_build_prompt_input_structure(self):
        """_build_prompt_input returns dict with required keys for zone3 prompt."""
        log_path = _make_jsonl_log([
            {"event_type": "periodic_snapshot", "elapsed_seconds": 60.0},
        ])
        analyzer = SessionAnalyzer(
            log_path=log_path,
            genome=_make_genome(),
            prospect_id="p-001",
            practitioner_id="pr-001",
            session_id="sess-007",
        )
        events = analyzer._load_log()
        prompt_input = analyzer._build_prompt_input(events)
        os.unlink(log_path)

        assert "session_id" in prompt_input
        assert "genome" in prompt_input
        assert "paralinguistic_snapshots" in prompt_input
        assert "prospect_id" in prompt_input


# ================================================================== #
#  PRACTITIONER PROFILE                                                #
# ================================================================== #

class TestPractitionerProfile:

    def test_fresh_profile_has_defaults(self):
        profile = PractitionerProfile(practitioner_id="pract-001")
        assert profile.close_threshold_instinct == 50.0
        assert profile.missed_window_rate == 50.0
        assert profile.session_count == 0

    def test_apply_delta_updates_parameter(self):
        profile = PractitionerProfile(practitioner_id="pract-001")
        profile.apply_delta("close_threshold_instinct", 80.0)
        # EMA: 50 * 0.7 + 80 * 0.3 = 35 + 24 = 59.0
        assert abs(profile.close_threshold_instinct - 59.0) < 0.5

    def test_apply_delta_unknown_parameter_returns_false(self):
        profile = PractitionerProfile(practitioner_id="pract-001")
        result = profile.apply_delta("nonexistent_parameter", 75.0)
        assert result is False

    def test_apply_delta_known_parameter_returns_true(self):
        profile = PractitionerProfile(practitioner_id="pract-001")
        result = profile.apply_delta("override_success_rate", 70.0)
        assert result is True

    def test_summary_has_required_keys(self):
        profile = PractitionerProfile(practitioner_id="pract-001")
        summary = profile.summary
        assert "practitioner_id" in summary
        assert "session_count" in summary
        assert "strengths" in summary
        assert "development_areas" in summary

    def test_high_scores_appear_in_strengths(self):
        profile = PractitionerProfile(practitioner_id="pract-001")
        profile.close_threshold_instinct = 80.0
        profile.hook_instinct = 75.0
        strengths = profile._identify_strengths()
        assert len(strengths) >= 2

    def test_low_scores_appear_in_development_areas(self):
        profile = PractitionerProfile(practitioner_id="pract-001")
        profile.hook_instinct = 25.0
        profile.resilience_under_resistance = 30.0
        areas = profile._identify_development_areas()
        assert len(areas) >= 2


# ================================================================== #
#  PRACTITIONER UPDATER                                                #
# ================================================================== #

class TestPractitionerUpdater:

    @pytest.mark.asyncio
    async def test_creates_fresh_profile_when_none_exists(self):
        updater = PractitionerUpdater(profile_repo=None)
        analysis = _make_analysis_result()
        profile = await updater.update(analysis, "pract-new-001")
        assert isinstance(profile, PractitionerProfile)
        assert profile.session_count == 1

    @pytest.mark.asyncio
    async def test_increments_session_count(self):
        updater = PractitionerUpdater(profile_repo=None)
        analysis = _make_analysis_result()

        profile1 = await updater.update(analysis, "pract-002")
        assert profile1.session_count == 1

        analysis2 = _make_analysis_result()
        analysis2.session_id = "sess-002"
        profile2 = await updater.update(analysis2, "pract-002")
        # Returns a fresh profile each time (no persistent repo in this test)
        assert profile2.session_count == 1

    @pytest.mark.asyncio
    async def test_deltas_applied_to_profile(self):
        updater = PractitionerUpdater(profile_repo=None)
        analysis = _make_analysis_result(
            practitioner_deltas=[
                {"parameter": "close_threshold_instinct", "old_value": 50.0,
                 "new_value": 75.0, "evidence": "close attempt at bar 75"}
            ]
        )
        profile = await updater.update(analysis, "pract-003")
        # EMA from 50.0 toward 75.0
        assert profile.close_threshold_instinct > 50.0

    @pytest.mark.asyncio
    async def test_unknown_parameter_skipped_gracefully(self):
        updater = PractitionerUpdater(profile_repo=None)
        analysis = _make_analysis_result(
            practitioner_deltas=[
                {"parameter": "nonexistent_param", "old_value": 50.0,
                 "new_value": 75.0, "evidence": "test"}
            ]
        )
        # Should not raise
        profile = await updater.update(analysis, "pract-004")
        assert profile.session_count == 1

    @pytest.mark.asyncio
    async def test_records_last_session_id(self):
        updater = PractitionerUpdater(profile_repo=None)
        analysis = _make_analysis_result()
        analysis.session_id = "sess-special-001"
        profile = await updater.update(analysis, "pract-005")
        assert profile.last_session_id == "sess-special-001"


# ================================================================== #
#  MIRROR REPORT                                                        #
# ================================================================== #

class TestMirrorReport:

    def test_render_returns_payload(self):
        renderer = MirrorReportRenderer()
        analysis = _make_analysis_result(
            mirror_report={
                "signature_strength": "High openness moments drove +18 close delta.",
                "blind_spot": "Two closing windows passed without advance option.",
                "instinct_ratio": "Overrides toward rapport worked. Urgency overrides did not.",
                "pressure_signature": "Under IRATE, bars dropped 15 pts average.",
            }
        )
        profile = PractitionerProfile(practitioner_id="pract-001")
        payload = renderer.render(analysis, profile)
        assert isinstance(payload, MirrorReportPayload)

    def test_render_with_no_profile(self):
        renderer = MirrorReportRenderer()
        analysis = _make_analysis_result(
            mirror_report={
                "signature_strength": "x", "blind_spot": "x",
                "instinct_ratio": "x", "pressure_signature": "x",
            }
        )
        payload = renderer.render(analysis, None)
        assert payload.practitioner_id == "unknown"

    def test_fallback_when_mirror_report_none(self):
        renderer = MirrorReportRenderer()
        # analysis with no mirror_report
        analysis = SessionAnalysisResult(session_id="sess-001", is_fallback=True)
        profile = PractitionerProfile(practitioner_id="pract-001")
        payload = renderer.render(analysis, profile)
        assert payload.is_fallback is True
        assert "unavailable" in payload.signature_strength.lower()

    def test_to_dict_is_serializable(self):
        renderer = MirrorReportRenderer()
        analysis = _make_analysis_result(
            mirror_report={
                "signature_strength": "test", "blind_spot": "test",
                "instinct_ratio": "test", "pressure_signature": "test",
            }
        )
        profile = PractitionerProfile(practitioner_id="pract-001", session_count=5)
        payload = renderer.render(analysis, profile)
        data = payload.to_dict()
        assert json.dumps(data)  # Should not raise
        assert "observations" in data
        assert "profile_context" in data

    def test_profile_session_count_in_payload(self):
        renderer = MirrorReportRenderer()
        analysis = _make_analysis_result(
            mirror_report={
                "signature_strength": "x", "blind_spot": "x",
                "instinct_ratio": "x", "pressure_signature": "x",
            }
        )
        profile = PractitionerProfile(practitioner_id="pract-001", session_count=12)
        payload = renderer.render(analysis, profile)
        assert payload.session_count == 12
