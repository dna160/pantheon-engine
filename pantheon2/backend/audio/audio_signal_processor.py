"""
Module: audio_signal_processor.py
Zone: 2 (Live session — no network, no cloud calls)
Input: AudioChunk (Stream B)
Output: AudioFeatureVector (raw feature values before paralinguistic interpretation)
LLM calls: 0
Side effects: None
Latency tolerance: <50ms per chunk

Stream B processor. Takes raw PCM chunks and extracts low-level audio
features: RMS energy, zero-crossing rate, spectral centroid, pitch estimate.
These raw features feed paralinguistic_extractor.py which interprets them
against the session baseline.

Uses librosa if available; falls back to numpy-only extraction if not.
"""

from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import structlog

from backend.audio.audio_buffer import AudioChunk

logger = structlog.get_logger(__name__)

SAMPLE_RATE = 16000  # Hz


@dataclass
class AudioFeatureVector:
    rms_energy: float              # Root-mean-square energy (volume proxy)
    zero_crossing_rate: float      # ZCR — proxy for noisiness / consonant density
    spectral_centroid: float       # Brightness — rises with tension/stress
    pitch_hz: float                # Fundamental frequency estimate (0 if unvoiced)
    timestamp: datetime
    chunk_index: int
    duration_ms: float = 50.0


class AudioSignalProcessor:
    """
    Extracts low-level audio features from raw PCM chunks (Stream B).
    No interpretation here — paralinguistic_extractor interprets the features.
    Zone 2 only. No cloud calls.
    """

    def __init__(self, sample_rate: int = SAMPLE_RATE) -> None:
        self._sample_rate = sample_rate
        self._librosa_available: Optional[bool] = None

    def _check_librosa(self) -> bool:
        if self._librosa_available is None:
            try:
                import librosa  # type: ignore
                self._librosa_available = True
            except ImportError:
                self._librosa_available = False
                logger.warning("audio_signal_processor.librosa_not_available — using numpy fallback")
        return self._librosa_available

    async def process_chunk(self, chunk: AudioChunk) -> AudioFeatureVector:
        """Extract features from one 50ms chunk. Non-blocking via executor."""
        return await asyncio.get_event_loop().run_in_executor(
            None, self._extract, chunk
        )

    def _extract(self, chunk: AudioChunk) -> AudioFeatureVector:
        import numpy as np

        raw = np.frombuffer(chunk.raw_bytes, dtype=np.int16).astype(np.float32)
        if len(raw) == 0:
            return AudioFeatureVector(
                rms_energy=0.0, zero_crossing_rate=0.0,
                spectral_centroid=0.0, pitch_hz=0.0,
                timestamp=chunk.timestamp, chunk_index=chunk.chunk_index,
            )

        # Normalize to [-1, 1]
        audio = raw / 32768.0

        # RMS energy
        rms = float(np.sqrt(np.mean(audio ** 2)))

        # Zero-crossing rate
        zcr = float(np.mean(np.abs(np.diff(np.sign(audio)))) / 2)

        # Spectral centroid and pitch via librosa if available
        if self._check_librosa():
            try:
                import librosa  # type: ignore
                spectral_centroid = float(
                    np.mean(librosa.feature.spectral_centroid(y=audio, sr=self._sample_rate))
                )
                f0, voiced, _ = librosa.pyin(
                    audio, fmin=50, fmax=500, sr=self._sample_rate
                )
                pitch_hz = float(np.nanmean(f0[voiced])) if voiced.any() else 0.0
            except Exception:
                spectral_centroid = self._numpy_spectral_centroid(audio)
                pitch_hz = 0.0
        else:
            spectral_centroid = self._numpy_spectral_centroid(audio)
            pitch_hz = 0.0

        return AudioFeatureVector(
            rms_energy=rms,
            zero_crossing_rate=zcr,
            spectral_centroid=spectral_centroid,
            pitch_hz=pitch_hz,
            timestamp=chunk.timestamp,
            chunk_index=chunk.chunk_index,
        )

    def _numpy_spectral_centroid(self, audio) -> float:
        """Numpy-only spectral centroid fallback."""
        import numpy as np
        fft = np.abs(np.fft.rfft(audio))
        freqs = np.fft.rfftfreq(len(audio), d=1.0 / self._sample_rate)
        total = np.sum(fft)
        if total == 0:
            return 0.0
        return float(np.sum(freqs * fft) / total)
