"""
tests/integration/test_zone2_loop.py
Phase 6 pass criteria — Zone 2 event loop integration.

Scope:
  Tests the full SessionRunner asyncio event loop with all external
  dependencies mocked. Verifies correct data flow between Stream A,
  Stream B, divergence detection, bar updates, dialog selection,
  HUD rendering, and session logging.

  No real audio, no real SLM, no Supabase, no network.

Tests:
  TestSessionRunnerInit   (3 tests)  — construction and initial state
  TestStreamALoop         (5 tests)  — verbal stream → classify → render
  TestStreamBLoop         (4 tests)  — para stream → bars-only render
  TestDivergenceDetection (3 tests)  — verbal/para mismatch → alert
  TestLoggerIntegration   (3 tests)  — event log calls
  TestSessionLifecycle    (3 tests)  — start, run, stop
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

# --- Domain imports ---
from backend.audio.audio_buffer import AudioBuffer, AudioChunk, AudioStream
from backend.audio.transcription_engine import TranscriptionEngine, TranscriptionResult
from backend.audio.audio_signal_processor import AudioSignalProcessor, AudioFeatureVector
from backend.audio.paralinguistic_extractor import ParalinguisticExtractor, ParalinguisticSignals
from backend.classifier.local_classifier import MomentType
from backend.classifier.moment_classifier import MomentClassifier, ClassificationResult
from backend.classifier.divergence_detector import DivergenceDetector, DivergenceAlert
from backend.bars.bar_calculator import BarCalculator, BarState
from backend.dialog.dialog_selector import DialogSelector, SelectionResult
from backend.display.display_driver import DisplayDriver, HUDPayload
from backend.session.session_runner import SessionRunner


# ================================================================== #
#  Factories                                                           #
# ================================================================== #

def _make_chunk(stream: AudioStream = AudioStream.A, idx: int = 0) -> AudioChunk:
    return AudioChunk(
        raw_bytes=b"\x00" * 1600,
        timestamp=datetime.now(timezone.utc),
        stream=stream,
        chunk_index=idx,
        duration_ms=50.0,
    )


def _make_transcription(text: str = "Let me think about this opportunity") -> TranscriptionResult:
    return TranscriptionResult(
        text=text,
        confidence=0.92,
        timestamp=datetime.now(timezone.utc),
        chunk_index_start=0,
        chunk_index_end=29,
        language_detected="id",
    )


def _make_feature_vector(idx: int = 0) -> AudioFeatureVector:
    return AudioFeatureVector(
        rms_energy=0.12,
        zero_crossing_rate=0.08,
        spectral_centroid=1800.0,
        pitch_hz=185.0,
        timestamp=datetime.now(timezone.utc),
        chunk_index=idx,
        duration_ms=50.0,
    )


def _make_para(**kwargs) -> ParalinguisticSignals:
    defaults = dict(
        speech_rate_delta=0.0,
        volume_level=0.6,
        pause_duration=1.2,
        voice_tension_index=0.2,
        cadence_consistency_score=0.85,
    )
    defaults.update(kwargs)
    return ParalinguisticSignals(**defaults)


def _make_classification(
    mtype: MomentType = MomentType.NEUTRAL_EXPLORATORY,
    confidence: float = 0.87,
) -> ClassificationResult:
    return ClassificationResult(
        moment_type=mtype,
        confidence=confidence,
        path="local",
        text_snippet="opportunity",
        timestamp=datetime.now(timezone.utc),
    )


def _make_bar_state(hook: int = 55, close: int = 35) -> BarState:
    return BarState(
        hook_score=hook,
        close_score=close,
        hook_trend="rising",
        close_trend="stable",
    )


def _make_selection(
    mtype: str = "neutral_exploratory",
    was_adapted: bool = True,
) -> SelectionResult:
    option = {
        "core_approach": "Acknowledge and explore",
        "base_language": "Tell me more about what you're weighing.",
        "trigger_phrase": "Explore the why",
        "base_probability": 68,
        "genome_rationale": "High chronesthesia — anchor to vision.",
    }
    return SelectionResult(
        moment_type=mtype,
        option_a=option,
        option_b={**option, "trigger_phrase": "Reframe to value"},
        option_c={**option, "trigger_phrase": "Slow and listen"},
        was_adapted=was_adapted,
        is_cache_fallback=False,
        classification_confidence=0.87,
    )


def _make_divergence_alert() -> DivergenceAlert:
    return DivergenceAlert(
        verbal_type=MomentType.HIGH_OPENNESS,
        tension_index=0.72,
        speech_rate_delta=0.31,
        volume_level=0.0,
        alert_message="Verbal openness / physiological activation mismatch.",
        practitioner_instruction="Do not accelerate to close. Surface the tension first.",
        timestamp=datetime.now(timezone.utc),
        severity="HIGH",
    )


# ================================================================== #
#  Runner builder                                                      #
# ================================================================== #

def _make_runner(
    *,
    buffer: Optional[AudioBuffer] = None,
    transcription_result: Optional[TranscriptionResult] = None,
    feature_vector: Optional[AudioFeatureVector] = None,
    para_signals: Optional[ParalinguisticSignals] = None,
    classification: Optional[ClassificationResult] = None,
    bar_state: Optional[BarState] = None,
    selection: Optional[SelectionResult] = None,
    divergence_alert: Optional[DivergenceAlert] = None,
    session_id: str = "sess-test-001",
) -> tuple[SessionRunner, dict]:
    """
    Build a fully-mocked SessionRunner. Returns (runner, mock_registry).
    mock_registry keys: transcription, signal_proc, para_extractor, classifier,
    divergence, bars, selector, display, logger
    """
    # Default values
    transcription_result = transcription_result or _make_transcription()
    feature_vector = feature_vector or _make_feature_vector()
    para_signals = para_signals or _make_para()
    classification = classification or _make_classification()
    bar_state = bar_state or _make_bar_state()
    selection = selection or _make_selection()

    # AudioBuffer — will be controlled by individual tests
    if buffer is None:
        buffer = AudioBuffer()

    # --- Component mocks ---
    mock_transcription = MagicMock(spec=TranscriptionEngine)
    mock_transcription.process_chunk = AsyncMock(return_value=transcription_result)

    mock_signal_proc = MagicMock(spec=AudioSignalProcessor)
    mock_signal_proc.process_chunk = AsyncMock(return_value=feature_vector)

    mock_para_extractor = MagicMock(spec=ParalinguisticExtractor)
    mock_para_extractor.update = MagicMock(return_value=para_signals)

    mock_classifier = MagicMock(spec=MomentClassifier)
    mock_classifier.classify = MagicMock(return_value=classification)

    mock_divergence = MagicMock(spec=DivergenceDetector)
    mock_divergence.detect = MagicMock(return_value=divergence_alert)

    mock_bars = MagicMock(spec=BarCalculator)
    mock_bars.update = MagicMock(return_value=bar_state)

    mock_selector = MagicMock(spec=DialogSelector)
    mock_selector.select = AsyncMock(return_value=selection)

    mock_display = MagicMock(spec=DisplayDriver)
    mock_display.render = MagicMock()
    mock_display.render_bars_only = MagicMock()
    mock_display.clear = MagicMock()

    mock_logger = MagicMock()
    mock_logger.log_divergence_alert = AsyncMock()
    mock_logger.log_moment_event = AsyncMock()
    mock_logger.log_periodic_snapshot = AsyncMock()
    mock_logger.log_option_choice = AsyncMock()

    runner = SessionRunner(
        audio_buffer=buffer,
        transcription_engine=mock_transcription,
        signal_processor=mock_signal_proc,
        para_extractor=mock_para_extractor,
        classifier=mock_classifier,
        divergence_detector=mock_divergence,
        bar_calculator=mock_bars,
        dialog_selector=mock_selector,
        display_driver=mock_display,
        session_logger=mock_logger,
        session_id=session_id,
    )

    mocks = {
        "transcription": mock_transcription,
        "signal_proc": mock_signal_proc,
        "para_extractor": mock_para_extractor,
        "classifier": mock_classifier,
        "divergence": mock_divergence,
        "bars": mock_bars,
        "selector": mock_selector,
        "display": mock_display,
        "logger": mock_logger,
    }
    return runner, mocks


async def _drive_stream_a(runner: SessionRunner, chunks: int = 1) -> None:
    """Push N chunks to Stream A then stop runner."""
    buf = runner._buffer
    for i in range(chunks):
        buf.push(b"\x00" * 1600)
    # Give event loop time to process
    await asyncio.sleep(0.05)
    runner.stop()


async def _drive_stream_b(runner: SessionRunner, chunks: int = 5) -> None:
    """Push N chunks to Stream B (via buf push) then stop runner."""
    buf = runner._buffer
    for i in range(chunks):
        buf.push(b"\x00" * 1600)
    await asyncio.sleep(0.05)
    runner.stop()


# ================================================================== #
#  TestSessionRunnerInit                                               #
# ================================================================== #

class TestSessionRunnerInit:

    def test_initial_state_not_running(self):
        runner, _ = _make_runner()
        assert runner._running is False

    def test_initial_state_no_classification(self):
        runner, _ = _make_runner()
        assert runner._latest_classification is None

    def test_initial_para_defaults(self):
        runner, _ = _make_runner()
        para = runner._latest_para
        assert isinstance(para, ParalinguisticSignals)
        assert para.voice_tension_index == 0.0
        assert para.volume_level == 0.5


# ================================================================== #
#  TestStreamALoop                                                     #
# ================================================================== #

class TestStreamALoop:

    def test_stream_a_calls_transcription(self):
        """Stream A: audio chunk → transcription_engine.process_chunk called."""
        runner, mocks = _make_runner()
        buf = runner._buffer

        async def _run():
            buf.push(b"\x00" * 1600)
            await asyncio.sleep(0.05)
            runner.stop()
            try:
                await asyncio.wait_for(runner.run(), timeout=1.0)
            except asyncio.TimeoutError:
                pass

        asyncio.run(_run())
        mocks["transcription"].process_chunk.assert_called()

    def test_stream_a_calls_classifier(self):
        """Stream A: transcription → moment_classifier.classify called."""
        runner, mocks = _make_runner()
        buf = runner._buffer

        async def _run():
            buf.push(b"\x00" * 1600)
            await asyncio.sleep(0.05)
            runner.stop()
            try:
                await asyncio.wait_for(runner.run(), timeout=1.0)
            except asyncio.TimeoutError:
                pass

        asyncio.run(_run())
        mocks["classifier"].classify.assert_called()

    def test_stream_a_calls_dialog_selector(self):
        """Stream A: classification → dialog_selector.select called."""
        runner, mocks = _make_runner()
        buf = runner._buffer

        async def _run():
            buf.push(b"\x00" * 1600)
            await asyncio.sleep(0.05)
            runner.stop()
            try:
                await asyncio.wait_for(runner.run(), timeout=1.0)
            except asyncio.TimeoutError:
                pass

        asyncio.run(_run())
        mocks["selector"].select.assert_called()

    def test_stream_a_calls_display_render(self):
        """Stream A: full pipeline → display_driver.render called."""
        runner, mocks = _make_runner()
        buf = runner._buffer

        async def _run():
            buf.push(b"\x00" * 1600)
            await asyncio.sleep(0.05)
            runner.stop()
            try:
                await asyncio.wait_for(runner.run(), timeout=1.0)
            except asyncio.TimeoutError:
                pass

        asyncio.run(_run())
        mocks["display"].render.assert_called()

    def test_stream_a_hud_payload_contains_para(self):
        """HUDPayload passed to render must include para field (G2 requirement)."""
        runner, mocks = _make_runner(
            para_signals=_make_para(voice_tension_index=0.4)
        )
        buf = runner._buffer
        captured_payload = []

        def capture_render(payload):
            captured_payload.append(payload)

        mocks["display"].render.side_effect = capture_render

        async def _run():
            buf.push(b"\x00" * 1600)
            await asyncio.sleep(0.05)
            runner.stop()
            try:
                await asyncio.wait_for(runner.run(), timeout=1.0)
            except asyncio.TimeoutError:
                pass

        asyncio.run(_run())

        assert len(captured_payload) >= 1
        payload = captured_payload[0]
        assert isinstance(payload, HUDPayload)
        # para must be set (G2 requirement from session_runner.py)
        assert payload.para is not None


# ================================================================== #
#  TestStreamBLoop                                                     #
# ================================================================== #

class TestStreamBLoop:

    def test_stream_b_calls_signal_processor(self):
        """Stream B: audio chunk → audio_signal_processor.process_chunk called."""
        runner, mocks = _make_runner()
        buf = runner._buffer

        async def _run():
            for _ in range(5):
                buf.push(b"\x00" * 1600)
            await asyncio.sleep(0.05)
            runner.stop()
            try:
                await asyncio.wait_for(runner.run(), timeout=1.0)
            except asyncio.TimeoutError:
                pass

        asyncio.run(_run())
        mocks["signal_proc"].process_chunk.assert_called()

    def test_stream_b_calls_para_extractor(self):
        """Stream B: feature vector → paralinguistic_extractor.update called."""
        runner, mocks = _make_runner()
        buf = runner._buffer

        async def _run():
            for _ in range(5):
                buf.push(b"\x00" * 1600)
            await asyncio.sleep(0.05)
            runner.stop()
            try:
                await asyncio.wait_for(runner.run(), timeout=1.0)
            except asyncio.TimeoutError:
                pass

        asyncio.run(_run())
        mocks["para_extractor"].update.assert_called()

    def test_stream_b_updates_latest_para(self):
        """Stream B: paralinguistic signals update shared _latest_para state."""
        high_tension_para = _make_para(voice_tension_index=0.85)
        runner, mocks = _make_runner(para_signals=high_tension_para)
        buf = runner._buffer

        async def _run():
            for _ in range(5):
                buf.push(b"\x00" * 1600)
            await asyncio.sleep(0.08)
            runner.stop()
            try:
                await asyncio.wait_for(runner.run(), timeout=1.0)
            except asyncio.TimeoutError:
                pass

        asyncio.run(_run())
        # After 5 chunks, _latest_para should have been updated
        assert runner._latest_para.voice_tension_index == 0.85

    def test_stream_b_render_bars_only_fires_at_interval(self):
        """Stream B: render_bars_only fires every PARA_RENDER_INTERVAL updates."""
        from backend.session.session_runner import PARA_RENDER_INTERVAL

        classification = _make_classification(MomentType.HIGH_OPENNESS)
        runner, mocks = _make_runner(classification=classification)
        # Force _latest_classification to be set so bars-only render can fire
        runner._latest_classification = classification
        buf = runner._buffer

        async def _run():
            # Push enough chunks for 1+ intervals
            for _ in range(PARA_RENDER_INTERVAL):
                buf.push(b"\x00" * 1600)
            await asyncio.sleep(0.1)
            runner.stop()
            try:
                await asyncio.wait_for(runner.run(), timeout=1.0)
            except asyncio.TimeoutError:
                pass

        asyncio.run(_run())
        mocks["display"].render_bars_only.assert_called()


# ================================================================== #
#  TestDivergenceDetection                                             #
# ================================================================== #

class TestDivergenceDetection:

    def test_divergence_alert_fires_when_detector_returns_alert(self):
        """When divergence_detector.detect returns alert, logger.log_divergence_alert called."""
        alert = _make_divergence_alert()
        runner, mocks = _make_runner(
            divergence_alert=alert,
            classification=_make_classification(MomentType.HIGH_OPENNESS),
        )
        buf = runner._buffer

        async def _run():
            buf.push(b"\x00" * 1600)
            await asyncio.sleep(0.05)
            runner.stop()
            try:
                await asyncio.wait_for(runner.run(), timeout=1.0)
            except asyncio.TimeoutError:
                pass

        asyncio.run(_run())
        mocks["logger"].log_divergence_alert.assert_called_once()
        logged_alert = mocks["logger"].log_divergence_alert.call_args[0][0]
        assert logged_alert.severity == "HIGH"

    def test_no_divergence_alert_when_detector_returns_none(self):
        """When divergence_detector.detect returns None, logger.log_divergence_alert NOT called."""
        runner, mocks = _make_runner(divergence_alert=None)
        buf = runner._buffer

        async def _run():
            buf.push(b"\x00" * 1600)
            await asyncio.sleep(0.05)
            runner.stop()
            try:
                await asyncio.wait_for(runner.run(), timeout=1.0)
            except asyncio.TimeoutError:
                pass

        asyncio.run(_run())
        mocks["logger"].log_divergence_alert.assert_not_called()

    def test_divergence_alert_stored_in_runner_state(self):
        """DivergenceAlert is stored in _active_divergence_alert for HUD payload."""
        alert = _make_divergence_alert()
        runner, mocks = _make_runner(divergence_alert=alert)
        buf = runner._buffer

        async def _run():
            buf.push(b"\x00" * 1600)
            await asyncio.sleep(0.05)
            runner.stop()
            try:
                await asyncio.wait_for(runner.run(), timeout=1.0)
            except asyncio.TimeoutError:
                pass

        asyncio.run(_run())
        assert runner._active_divergence_alert is not None
        assert runner._active_divergence_alert.severity == "HIGH"


# ================================================================== #
#  TestLoggerIntegration                                               #
# ================================================================== #

class TestLoggerIntegration:

    def test_log_moment_event_called_per_stream_a_cycle(self):
        """session_logger.log_moment_event is called for each Stream A transcription."""
        runner, mocks = _make_runner()
        buf = runner._buffer

        async def _run():
            buf.push(b"\x00" * 1600)
            await asyncio.sleep(0.05)
            runner.stop()
            try:
                await asyncio.wait_for(runner.run(), timeout=1.0)
            except asyncio.TimeoutError:
                pass

        asyncio.run(_run())
        mocks["logger"].log_moment_event.assert_called()

    def test_log_moment_event_receives_correct_session_id(self):
        """log_moment_event is called with the runner's session_id."""
        runner, mocks = _make_runner(session_id="sess-test-789")
        buf = runner._buffer

        async def _run():
            buf.push(b"\x00" * 1600)
            await asyncio.sleep(0.05)
            runner.stop()
            try:
                await asyncio.wait_for(runner.run(), timeout=1.0)
            except asyncio.TimeoutError:
                pass

        asyncio.run(_run())
        call_kwargs = mocks["logger"].log_moment_event.call_args.kwargs
        assert call_kwargs.get("session_id") == "sess-test-789"

    def test_option_choice_log_called_via_record_option_choice(self):
        """record_option_choice() delegates to logger.log_option_choice correctly."""
        runner, mocks = _make_runner()
        runner._latest_classification = _make_classification()
        runner._latest_bar_state = _make_bar_state()
        selection = _make_selection()

        asyncio.run(
            runner.record_option_choice("option_a", selection)
        )

        mocks["logger"].log_option_choice.assert_called_once()
        kwargs = mocks["logger"].log_option_choice.call_args.kwargs
        assert kwargs["option_key"] == "option_a"
        assert kwargs["session_id"] == "sess-test-001"


# ================================================================== #
#  TestSessionLifecycle                                                #
# ================================================================== #

class TestSessionLifecycle:

    def test_runner_sets_running_true_when_started(self):
        """_running is True while run() is active."""
        runner, mocks = _make_runner()
        running_during = []

        async def _run():
            task = asyncio.create_task(runner.run())
            await asyncio.sleep(0.01)
            running_during.append(runner._running)
            runner.stop()
            try:
                await asyncio.wait_for(task, timeout=0.5)
            except asyncio.TimeoutError:
                task.cancel()

        asyncio.run(_run())
        assert True in running_during

    def test_stop_sets_running_false(self):
        """stop() sets _running to False."""
        runner, mocks = _make_runner()

        async def _run():
            task = asyncio.create_task(runner.run())
            await asyncio.sleep(0.01)
            runner.stop()
            try:
                await asyncio.wait_for(task, timeout=0.5)
            except asyncio.TimeoutError:
                task.cancel()

        asyncio.run(_run())
        assert runner._running is False

    def test_display_clear_called_on_stop(self):
        """display_driver.clear() is called when session ends."""
        runner, mocks = _make_runner()

        async def _run():
            task = asyncio.create_task(runner.run())
            await asyncio.sleep(0.01)
            runner.stop()
            try:
                await asyncio.wait_for(task, timeout=0.5)
            except asyncio.TimeoutError:
                task.cancel()

        asyncio.run(_run())
        mocks["display"].clear.assert_called_once()
