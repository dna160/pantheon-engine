"""
Module: session_runner.py
Zone: 2 (Live session — NO NETWORK. NO CLOUD CALLS. LOCAL ONLY.)
Input: AudioBuffer + all pre-warmed Zone 2 components
Output: Continuous HUD updates to DisplayDriver + event logs
LLM calls: 0 (SLM only — local, no cloud)
Side effects: Updates display hardware, writes to session_logger
Latency tolerance: <400ms end-to-end per PRD 1.1

THE ZONE 2 EVENT LOOP.

Architecture: Two parallel asyncio tasks (STREAM A + STREAM B) run
simultaneously from the moment the practitioner presses GO.

  STREAM A — TRANSCRIPT (verbal):
    audio_buffer → transcription_engine → moment_classifier
    → verbal ClassificationResult → bar_calculator (verbal input)
    → dialog_selector (cache + SLM live adaptation)
    → display_driver.render(full HUD update)

  STREAM B — PARALINGUISTICS (how it's said):
    audio_buffer → audio_signal_processor → paralinguistic_extractor
    → ParalinguisticSignals → divergence_detector (check vs. verbal)
    → bar_calculator (para modulation)
    → display_driver.render_bars_only (lightweight update)

  SESSION LOGGER:
    Runs as a third asyncio task. Writes event on:
      - moment type change
      - 30-second snapshot
      - divergence alert
      - practitioner option choice

CRITICAL: This module never calls any external API.
All processing is local. Zero network dependency.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Optional

import structlog

from backend.audio.audio_bridge import AudioBridge
from backend.audio.audio_buffer import AudioBuffer
from backend.audio.transcription_engine import TranscriptionEngine
from backend.audio.audio_signal_processor import AudioSignalProcessor
from backend.audio.paralinguistic_extractor import ParalinguisticExtractor, ParalinguisticSignals
from backend.classifier.moment_classifier import MomentClassifier, ClassificationResult
from backend.classifier.divergence_detector import DivergenceDetector
from backend.bars.bar_calculator import BarCalculator, BarState
from backend.dialog.dialog_selector import DialogSelector
from backend.display.display_driver import DisplayDriver, HUDPayload

logger = structlog.get_logger(__name__)

# Stream B fires a bars-only render every N paralinguistic updates
# (not every chunk — too high frequency for display refresh)
PARA_RENDER_INTERVAL = 5       # Every 5 Stream B updates → bars-only render


class SessionRunner:
    """
    Zone 2 event loop. Orchestrates both audio streams and all downstream
    processing. Constructed in Zone 1 (via harness_runner) with all pre-warmed
    components injected. Activated by practitioner GO signal.

    Zone 2 only. No cloud calls. No network. Local SLM only.
    """

    def __init__(
        self,
        audio_buffer: AudioBuffer,
        transcription_engine: TranscriptionEngine,
        signal_processor: AudioSignalProcessor,
        para_extractor: ParalinguisticExtractor,
        classifier: MomentClassifier,
        divergence_detector: DivergenceDetector,
        bar_calculator: BarCalculator,
        dialog_selector: DialogSelector,
        display_driver: DisplayDriver,
        session_logger,                         # session_logger.SessionLogger
        session_id: str,
    ) -> None:
        self._buffer = audio_buffer
        self._transcription = transcription_engine
        self._signal_proc = signal_processor
        self._para = para_extractor
        self._classifier = classifier
        self._divergence = divergence_detector
        self._bars = bar_calculator
        self._selector = dialog_selector
        self._display = display_driver
        self._logger = session_logger
        self._session_id = session_id

        # Shared state — updated by both streams, read by render path
        # GIL-safe for simple attribute assignment in CPython async context
        self._latest_para: ParalinguisticSignals = ParalinguisticSignals()
        self._latest_classification: Optional[ClassificationResult] = None
        self._latest_bar_state: Optional[BarState] = None
        self._active_divergence_alert = None

        self._session_start: Optional[float] = None
        self._running: bool = False
        self._para_update_count: int = 0

    async def run(self) -> None:
        """
        Main entry point. Starts both streams and runs until stop() is called.
        Called by harness_runner after practitioner GO signal.
        """
        self._running = True
        self._session_start = time.monotonic()

        logger.info("session_runner.started", session_id=self._session_id)

        try:
            await asyncio.gather(
                self._stream_a_loop(),
                self._stream_b_loop(),
                self._logger_loop(),
            )
        except asyncio.CancelledError:
            pass
        finally:
            self._running = False
            self._display.clear()
            logger.info("session_runner.stopped", session_id=self._session_id)

    def stop(self) -> None:
        """Signal the session to end. Cancels all running tasks."""
        self._running = False

    # ================================================================== #
    #  STREAM A — TRANSCRIPT (VERBAL)                                      #
    # ================================================================== #

    async def _stream_a_loop(self) -> None:
        """
        Stream A: Audio chunks → transcript → moment classification → HUD render.
        Full render path — includes dialog_selector + SLM adaptation.
        """
        while self._running:
            try:
                chunk = await asyncio.wait_for(
                    self._buffer.get_stream_a(), timeout=2.0
                )
            except asyncio.TimeoutError:
                continue

            # Accumulate + transcribe (returns None until 1.5s window is full)
            transcription = await self._transcription.process_chunk(chunk)
            if transcription is None or not transcription.text.strip():
                continue

            elapsed = self._elapsed_seconds()

            # Classify moment type
            classification = self._classifier.classify(transcription, elapsed)
            self._latest_classification = classification

            # Update bars with verbal classification + latest para signals
            bar_state = self._bars.update(classification, self._latest_para)
            self._latest_bar_state = bar_state

            # Check divergence (verbal vs. paralinguistic)
            alert = self._divergence.detect(classification, self._latest_para)
            if alert is not None:
                self._active_divergence_alert = alert
                await self._logger.log_divergence_alert(alert)
                logger.info(
                    "session_runner.divergence_alert",
                    severity=getattr(alert, "severity", "?"),
                    moment=classification.moment_type.value,
                )

            # Dialog selection + SLM adaptation (may take up to 350ms)
            selection = await self._selector.select(
                classification,
                self._latest_para,
            )

            # Full HUD render — pass para so phone_driver can emit HiddenSignalPanel
            payload = HUDPayload(
                bar_state=bar_state,
                selection=selection,
                session_elapsed_seconds=elapsed,
                divergence_alert=self._active_divergence_alert,
                para=self._latest_para,         # G2: Stream B → HiddenSignalPanel
                # confidence_badge passed as None here — phone_driver uses default (MEDIUM/yellow)
                # TODO: thread confidence_badge from SessionBundle through to SessionRunner
            )
            self._display.render(payload)

            # Log moment type event
            await self._logger.log_moment_event(
                session_id=self._session_id,
                classification=classification,
                bar_state=bar_state,
                selection=selection,
            )

    # ================================================================== #
    #  STREAM B — PARALINGUISTICS                                          #
    # ================================================================== #

    async def _stream_b_loop(self) -> None:
        """
        Stream B: Audio chunks → feature extraction → paralinguistic signals.
        Lightweight bars-only render on every PARA_RENDER_INTERVAL updates.
        """
        while self._running:
            try:
                chunk = await asyncio.wait_for(
                    self._buffer.get_stream_b(), timeout=2.0
                )
            except asyncio.TimeoutError:
                continue

            # Feature extraction
            fv = await self._signal_proc.process_chunk(chunk)
            if fv is None:
                continue

            # Paralinguistic signals
            para = self._para.update(fv)
            self._latest_para = para

            self._para_update_count += 1

            # Lightweight bars-only render at reduced frequency
            if (
                self._para_update_count % PARA_RENDER_INTERVAL == 0
                and self._latest_classification is not None
            ):
                # Re-run bar update with new para signals
                bar_state = self._bars.update(
                    self._latest_classification, para
                )
                self._latest_bar_state = bar_state
                self._display.render_bars_only(bar_state)

    # ================================================================== #
    #  SESSION LOGGER LOOP                                                  #
    # ================================================================== #

    async def _logger_loop(self) -> None:
        """
        Periodic snapshot loop. Writes paralinguistic snapshot every 30 seconds.
        The session_logger also receives direct calls from _stream_a_loop
        for moment-type-change and option-choice events.
        """
        while self._running:
            await asyncio.sleep(30)
            if not self._running:
                break

            await self._logger.log_periodic_snapshot(
                session_id=self._session_id,
                para=self._latest_para,
                bar_state=self._latest_bar_state,
                elapsed_seconds=self._elapsed_seconds(),
            )

    # ================================================================== #
    #  Helpers                                                              #
    # ================================================================== #

    def _elapsed_seconds(self) -> float:
        if self._session_start is None:
            return 0.0
        return time.monotonic() - self._session_start

    async def record_option_choice(
        self,
        option_key: str,
        selection_result,
    ) -> None:
        """
        Called by the mobile app (via FastAPI endpoint) when the practitioner
        taps an option on the phone HUD. Writes to session log.
        """
        await self._logger.log_option_choice(
            session_id=self._session_id,
            option_key=option_key,
            selection_result=selection_result,
            classification=self._latest_classification,
            bar_state=self._latest_bar_state,
        )
