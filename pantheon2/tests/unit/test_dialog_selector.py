"""
tests/unit/test_dialog_selector.py
Phase 3 pass criteria — Dialog Selector tests.

Tests:
  TestDialogSelector (10 tests)
"""

from __future__ import annotations

import asyncio
import copy
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from backend.dialog.dialog_selector import DialogSelector, SelectionResult
from backend.classifier.local_classifier import MomentType
from backend.classifier.moment_classifier import ClassificationResult
from backend.audio.paralinguistic_extractor import ParalinguisticSignals


# ================================================================== #
#  Helpers                                                             #
# ================================================================== #

def _make_classification(
    mtype: MomentType = MomentType.HIGH_OPENNESS,
    confidence: float = 0.85,
) -> ClassificationResult:
    return ClassificationResult(
        moment_type=mtype,
        confidence=confidence,
        path="local",
        text_snippet="test snippet",
        timestamp=datetime.now(timezone.utc),
    )


def _make_para(**kwargs) -> ParalinguisticSignals:
    defaults = dict(
        speech_rate_delta=0.0,
        volume_level=0.5,
        pause_duration=0.0,
        voice_tension_index=0.3,
        cadence_consistency_score=0.9,
    )
    defaults.update(kwargs)
    return ParalinguisticSignals(**defaults)


def _make_cache() -> dict:
    """Build a minimal valid cache dict with all 6 moment types."""
    option_template = {
        "core_approach": "Test approach",
        "base_language": "Test language",
        "trigger_phrase": "Test phrase",
        "base_probability": 60,
        "genome_rationale": "Test rationale",
    }
    cache = {}
    for mtype in [
        "neutral_exploratory", "irate_resistant", "topic_avoidance",
        "identity_threat", "high_openness", "closing_signal",
    ]:
        cache[mtype] = {
            "option_a": dict(option_template, base_probability=65),
            "option_b": dict(option_template, base_probability=55),
            "option_c": dict(option_template, base_probability=45),
        }
    cache["_is_fallback"] = False
    return cache


# ================================================================== #
#  DIALOG SELECTOR                                                      #
# ================================================================== #

class TestDialogSelector:

    @pytest.mark.asyncio
    async def test_returns_selection_result(self):
        selector = DialogSelector(cache=_make_cache())
        result = await selector.select(_make_classification(), _make_para())
        assert isinstance(result, SelectionResult)

    @pytest.mark.asyncio
    async def test_moment_type_matches_classification(self):
        selector = DialogSelector(cache=_make_cache())
        classification = _make_classification(MomentType.IRATE_RESISTANT)
        result = await selector.select(classification, _make_para())
        assert result.moment_type == "irate_resistant"

    @pytest.mark.asyncio
    async def test_options_populated_from_cache(self):
        selector = DialogSelector(cache=_make_cache())
        result = await selector.select(_make_classification(), _make_para())
        assert isinstance(result.option_a, dict)
        assert isinstance(result.option_b, dict)
        assert isinstance(result.option_c, dict)
        assert "base_language" in result.option_a

    @pytest.mark.asyncio
    async def test_no_cache_returns_hardcoded_fallback(self):
        selector = DialogSelector(cache=None)
        result = await selector.select(_make_classification(), _make_para())
        assert result.is_cache_fallback is True
        assert result.option_a.get("base_language") != ""

    @pytest.mark.asyncio
    async def test_missing_moment_type_returns_fallback(self):
        """Cache exists but moment type is missing — should return fallback."""
        sparse_cache = {"neutral_exploratory": {
            "option_a": {"base_language": "x", "base_probability": 50},
            "option_b": {"base_language": "y", "base_probability": 50},
            "option_c": {"base_language": "z", "base_probability": 50},
        }}
        selector = DialogSelector(cache=sparse_cache)
        result = await selector.select(
            _make_classification(MomentType.CLOSING_SIGNAL), _make_para()
        )
        assert result.is_cache_fallback is True

    @pytest.mark.asyncio
    async def test_slm_adapter_called_when_present(self):
        mock_adapter = MagicMock()
        mock_adapter.adapt_options = AsyncMock(return_value={
            "option_a": {"base_language": "adapted a", "base_probability": 70},
            "option_b": {"base_language": "adapted b", "base_probability": 55},
            "option_c": {"base_language": "adapted c", "base_probability": 45},
        })

        selector = DialogSelector(cache=_make_cache(), slm_adapter=mock_adapter)
        result = await selector.select(_make_classification(), _make_para())

        mock_adapter.adapt_options.assert_called_once()
        # Adapted language should be in result
        assert result.option_a.get("base_language") == "adapted a"
        assert result.was_adapted is True

    @pytest.mark.asyncio
    async def test_fallback_when_adapter_raises(self):
        """If SLM adapter raises, should fall back to base cache options."""
        mock_adapter = MagicMock()
        mock_adapter.adapt_options = AsyncMock(side_effect=RuntimeError("SLM crashed"))

        selector = DialogSelector(cache=_make_cache(), slm_adapter=mock_adapter)
        result = await selector.select(_make_classification(), _make_para())

        # Should still return valid result (fallback to cache)
        assert isinstance(result, SelectionResult)
        assert result.was_adapted is False
        assert "base_language" in result.option_a

    @pytest.mark.asyncio
    async def test_no_adapter_was_adapted_false(self):
        selector = DialogSelector(cache=_make_cache(), slm_adapter=None)
        result = await selector.select(_make_classification(), _make_para())
        assert result.was_adapted is False

    @pytest.mark.asyncio
    async def test_confidence_preserved_in_result(self):
        selector = DialogSelector(cache=_make_cache())
        classification = _make_classification(confidence=0.72)
        result = await selector.select(classification, _make_para())
        assert abs(result.classification_confidence - 0.72) < 0.001

    @pytest.mark.asyncio
    async def test_update_cache_replaces_options(self):
        selector = DialogSelector(cache=None)

        # Initially no cache
        result_before = await selector.select(_make_classification(), _make_para())
        assert result_before.is_cache_fallback is True

        # Load new cache
        selector.update_cache(_make_cache())

        result_after = await selector.select(_make_classification(), _make_para())
        assert result_after.is_cache_fallback is False
