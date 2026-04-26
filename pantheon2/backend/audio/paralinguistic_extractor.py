"""
Module: paralinguistic_extractor.py
Zone: 2 (Live session — no network, no cloud calls)
Input: AudioFeatureVector stream + session baseline (established in first 90s)
Output: ParalinguisticSignals — interpreted deltas vs. baseline
LLM calls: 0
Side effects: Writes to ObservedState (paralinguistic fields only)
Latency tolerance: <20ms per update

Interprets AudioFeatureVectors against the session-specific baseline
established in the first 90 seconds (basa-basi phase in Indonesian B2B).
Produces the 5 paralinguistic signals defined in PRD 3.1a:
  - speech_rate_delta: change from baseline (normalized, -1.0 to +1.0)
  - volume_level: normalized against room ambient (0.0–1.0)
  - pause_duration: silence after practitioner speaks (seconds)
  - voice_tension_index: pitch variance + vocal fry proxy (0.0–1.0)
  - cadence_consistency_score: rhythm regularity (0.0–1.0)

BASELINE: captured during first 90 seconds (BASELINE_DURATION_S = 90).
Session-specific only. No cross-session averaging.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import structlog

from backend.audio.audio_signal_processor import AudioFeatureVector

logger = structlog.get_logger(__name__)

BASELINE_DURATION_S: float = 90.0  # First 90s = basa-basi / baseline capture
SILENCE_THRESHOLD_RMS: float = 0.01  # Below this RMS = silence


@dataclass
class ParalinguisticBaseline:
    """Session-specific baseline captured during first 90 seconds."""
    mean_rms: float = 0.05
    mean_zcr: float = 0.1
    mean_spectral_centroid: float = 1500.0
    mean_pitch_hz: float = 150.0
    pitch_variance: float = 20.0
    captured_at: Optional[datetime] = None
    is_established: bool = False


@dataclass
class ParalinguisticSignals:
    """
    The 5 paralinguistic signals from PRD 3.1a.
    These populate ObservedState.paralinguistic fields.
    """
    speech_rate_delta: float = 0.0      # -1.0 (slower) to +1.0 (faster) vs. baseline
    volume_level: float = 0.5           # 0.0–1.0, normalized against ambient
    pause_duration: float = 0.0         # seconds of silence after last practitioner utterance
    voice_tension_index: float = 0.0    # 0.0–1.0: pitch variance + spectral brightness proxy
    cadence_consistency_score: float = 1.0  # 0.0–1.0: rhythm regularity
    timestamp: Optional[datetime] = None


class ParalinguisticExtractor:
    """
    Maintains session baseline and extracts interpreted paralinguistic signals
    from AudioFeatureVector stream. Zone 2 only. No cloud calls.
    """

    ROLLING_WINDOW = 10  # Feature vectors to average for current state

    def __init__(self) -> None:
        self._baseline = ParalinguisticBaseline()
        self._baseline_vectors: list[AudioFeatureVector] = []
        self._baseline_window_s: float = BASELINE_DURATION_S
        self._rolling_buffer: list[AudioFeatureVector] = []
        self._silence_start: Optional[datetime] = None
        self._last_rms: float = 0.0

    def update(self, fv: AudioFeatureVector) -> ParalinguisticSignals:
        """
        Process one AudioFeatureVector. Returns current ParalinguisticSignals.
        Updates baseline during first 90 seconds. Always non-blocking.
        """
        self._maybe_update_baseline(fv)

        # Rolling buffer for current state smoothing
        self._rolling_buffer.append(fv)
        if len(self._rolling_buffer) > self.ROLLING_WINDOW:
            self._rolling_buffer.pop(0)

        return self._compute_signals()

    def _maybe_update_baseline(self, fv: AudioFeatureVector) -> None:
        """Accumulate baseline during first 90 seconds of session."""
        if self._baseline.is_established:
            return
        self._baseline_vectors.append(fv)

        # Check if 90 seconds have elapsed
        if len(self._baseline_vectors) >= 2:
            first_ts = self._baseline_vectors[0].timestamp
            last_ts = fv.timestamp
            elapsed = (last_ts - first_ts).total_seconds()
            if elapsed >= self._baseline_window_s:
                self._establish_baseline()

    def _establish_baseline(self) -> None:
        vecs = self._baseline_vectors
        if not vecs:
            return
        rms_vals = [v.rms_energy for v in vecs]
        zcr_vals = [v.zero_crossing_rate for v in vecs]
        sc_vals = [v.spectral_centroid for v in vecs]
        pitch_vals = [v.pitch_hz for v in vecs if v.pitch_hz > 0]

        self._baseline = ParalinguisticBaseline(
            mean_rms=statistics.mean(rms_vals) if rms_vals else 0.05,
            mean_zcr=statistics.mean(zcr_vals) if zcr_vals else 0.1,
            mean_spectral_centroid=statistics.mean(sc_vals) if sc_vals else 1500.0,
            mean_pitch_hz=statistics.mean(pitch_vals) if pitch_vals else 150.0,
            pitch_variance=statistics.stdev(pitch_vals) if len(pitch_vals) > 1 else 20.0,
            captured_at=datetime.now(timezone.utc),
            is_established=True,
        )
        logger.info(
            "paralinguistic.baseline_established",
            mean_rms=round(self._baseline.mean_rms, 4),
            mean_pitch=round(self._baseline.mean_pitch_hz, 1),
            samples=len(vecs),
        )

    def _compute_signals(self) -> ParalinguisticSignals:
        if not self._rolling_buffer:
            return ParalinguisticSignals(timestamp=datetime.now(timezone.utc))

        current_rms = statistics.mean(v.rms_energy for v in self._rolling_buffer)
        current_zcr = statistics.mean(v.zero_crossing_rate for v in self._rolling_buffer)
        current_sc = statistics.mean(v.spectral_centroid for v in self._rolling_buffer)
        pitch_vals = [v.pitch_hz for v in self._rolling_buffer if v.pitch_hz > 0]
        current_pitch_var = statistics.stdev(pitch_vals) if len(pitch_vals) > 1 else 0.0

        b = self._baseline

        # speech_rate_delta: ZCR delta vs baseline (ZCR correlates with speech rate)
        if b.mean_zcr > 0:
            speech_rate_delta = min(1.0, max(-1.0, (current_zcr - b.mean_zcr) / b.mean_zcr))
        else:
            speech_rate_delta = 0.0

        # volume_level: normalized RMS against baseline ambient
        if b.mean_rms > 0:
            volume_level = min(1.0, current_rms / (b.mean_rms * 3.0))
        else:
            volume_level = min(1.0, current_rms / 0.15)

        # pause_duration: detect silence and track duration
        is_silent = current_rms < SILENCE_THRESHOLD_RMS
        now = datetime.now(timezone.utc)
        if is_silent:
            if self._silence_start is None:
                self._silence_start = now
            pause_duration = (now - self._silence_start).total_seconds()
        else:
            self._silence_start = None
            pause_duration = 0.0

        # voice_tension_index: pitch variance + spectral brightness above baseline
        pitch_var_norm = min(1.0, current_pitch_var / max(b.pitch_variance * 3.0, 1.0))
        sc_norm = min(1.0, max(0.0, (current_sc - b.mean_spectral_centroid) / max(b.mean_spectral_centroid, 1.0)))
        voice_tension_index = min(1.0, (pitch_var_norm * 0.6 + sc_norm * 0.4))

        # cadence_consistency: inverse of pitch_var within rolling window
        # High variance = broken cadence = low consistency
        cadence_consistency = max(0.0, 1.0 - pitch_var_norm)

        return ParalinguisticSignals(
            speech_rate_delta=round(speech_rate_delta, 3),
            volume_level=round(volume_level, 3),
            pause_duration=round(pause_duration, 2),
            voice_tension_index=round(voice_tension_index, 3),
            cadence_consistency_score=round(cadence_consistency, 3),
            timestamp=now,
        )

    @property
    def baseline(self) -> ParalinguisticBaseline:
        return self._baseline
