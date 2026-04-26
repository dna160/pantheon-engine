"""
Module: transcription_engine.py
Zone: 2 (Live session — no network, no cloud calls)
Input: AudioChunk (Stream A)
Output: TranscriptionResult (text, confidence, timestamp)
LLM calls: 0
Side effects: None
Latency tolerance: <150ms per chunk (Whisper small on-device target)

Stream A processor. Takes 50ms PCM chunks from AudioBuffer Stream A,
accumulates into 1–2s windows, and runs local Whisper small transcription.
All inference is on-device. No cloud calls.

Whisper model loading is deferred until first use (lazy init) to avoid
blocking Zone 1 setup. slm_warmer.py triggers warm-up pre-session.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import structlog

from backend.audio.audio_buffer import AudioChunk

logger = structlog.get_logger(__name__)

# Accumulate ~1.5s of audio before transcribing (30 × 50ms chunks)
CHUNKS_PER_WINDOW = 30


@dataclass
class TranscriptionResult:
    text: str
    confidence: float         # 0.0–1.0
    timestamp: datetime
    chunk_index_start: int
    chunk_index_end: int
    language_detected: str = "id"   # default Indonesian


class TranscriptionEngine:
    """
    Wraps local Whisper small model for on-device transcription.
    Accumulates 50ms chunks into 1.5s windows before inference.
    Falls back to empty string on model error — never raises.
    Zone 2 only. No cloud calls.
    """

    def __init__(self, model_size: str = "small", language: str = "id") -> None:
        self._model_size = model_size
        self._language = language
        self._model = None       # lazy-loaded
        self._chunk_buffer: list[AudioChunk] = []

    def warm_up(self) -> None:
        """
        Pre-loads Whisper model into memory. Called by slm_warmer.py pre-session.
        Silently skips if whisper package not installed (test environment).
        """
        try:
            import whisper  # type: ignore
            self._model = whisper.load_model(self._model_size)
            logger.info("transcription_engine.warmed", model=self._model_size)
        except ImportError:
            logger.warning("transcription_engine.whisper_not_installed — running in stub mode")
        except Exception as e:
            logger.warning("transcription_engine.warm_failed", error=str(e))

    async def process_chunk(self, chunk: AudioChunk) -> Optional[TranscriptionResult]:
        """
        Accumulate chunk. Returns TranscriptionResult once window is full,
        None otherwise. Always non-blocking.
        """
        self._chunk_buffer.append(chunk)

        if len(self._chunk_buffer) < CHUNKS_PER_WINDOW:
            return None

        window = self._chunk_buffer.copy()
        self._chunk_buffer.clear()

        return await asyncio.get_event_loop().run_in_executor(
            None, self._transcribe_window, window
        )

    def _transcribe_window(self, chunks: list[AudioChunk]) -> TranscriptionResult:
        start_idx = chunks[0].chunk_index
        end_idx = chunks[-1].chunk_index
        ts = chunks[-1].timestamp

        if self._model is None:
            # Stub mode — return empty result (tests + environments without Whisper)
            return TranscriptionResult(
                text="",
                confidence=0.0,
                timestamp=ts,
                chunk_index_start=start_idx,
                chunk_index_end=end_idx,
            )

        try:
            import numpy as np  # type: ignore
            import io, wave

            # Combine raw PCM bytes into numpy float32 array
            raw = b"".join(c.raw_bytes for c in chunks)
            audio_array = (
                np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
            )

            result = self._model.transcribe(
                audio_array,
                language=self._language,
                fp16=False,
            )
            text = result.get("text", "").strip()
            return TranscriptionResult(
                text=text,
                confidence=0.85,   # Whisper small does not expose per-segment confidence easily
                timestamp=ts,
                chunk_index_start=start_idx,
                chunk_index_end=end_idx,
                language_detected=self._language,
            )
        except Exception as e:
            logger.warning("transcription_engine.error", error=str(e))
            return TranscriptionResult(
                text="",
                confidence=0.0,
                timestamp=ts,
                chunk_index_start=start_idx,
                chunk_index_end=end_idx,
            )
