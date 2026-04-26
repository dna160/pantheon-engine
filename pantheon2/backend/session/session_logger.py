"""
Module: session_logger.py
Zone: 2 (Live session — no network, no cloud calls)
Input: Events from session_runner (moment changes, para snapshots, option choices)
Output: Structured event log (JSONL file, one event per line)
LLM calls: 0
Side effects: Writes to session log file on disk
Latency tolerance: <5ms per write (async non-blocking)

Session event logger. Writes four categories of events:
  1. moment_event — on every new ClassificationResult (verbal stream change)
  2. periodic_snapshot — every 30 seconds (para + bars)
  3. divergence_alert — when verbal ≠ paralinguistic signals
  4. option_choice — when practitioner taps an option on the HUD

Log format: JSONL (one JSON object per line).
Log file: {session_id}_{date}.jsonl
Used by Zone 3 session_analyzer.py for post-session mutation review.
"""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import structlog

from backend.audio.paralinguistic_extractor import ParalinguisticSignals
from backend.bars.bar_calculator import BarState
from backend.classifier.moment_classifier import ClassificationResult
from backend.dialog.dialog_selector import SelectionResult

logger = structlog.get_logger(__name__)

# Default log directory (override via LOG_DIR env var)
DEFAULT_LOG_DIR = "./session_logs"


class SessionLogger:
    """
    Async session event logger.
    Writes structured JSONL events to disk for Zone 3 analysis.
    Zone 2 only. No cloud calls.
    """

    def __init__(self, session_id: str, log_dir: Optional[str] = None) -> None:
        self._session_id = session_id
        self._log_dir = Path(log_dir or os.getenv("LOG_DIR", DEFAULT_LOG_DIR))
        self._log_file: Optional[Path] = None
        self._lock = asyncio.Lock()
        self._event_count = 0

    async def open(self) -> None:
        """
        Create log file. Must be called before any log_* methods.
        Creates log directory if it doesn't exist.
        """
        self._log_dir.mkdir(parents=True, exist_ok=True)
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"{self._session_id}_{date_str}.jsonl"
        self._log_file = self._log_dir / filename
        logger.info(
            "session_logger.opened",
            file=str(self._log_file),
        )

    async def close(self) -> None:
        """Flush any pending writes and close the log."""
        await self._write({
            "event_type": "session_end",
            "session_id": self._session_id,
            "total_events": self._event_count,
        })
        logger.info(
            "session_logger.closed",
            events_written=self._event_count,
        )

    # ================================================================== #
    #  Event Writers                                                        #
    # ================================================================== #

    async def log_moment_event(
        self,
        session_id: str,
        classification: ClassificationResult,
        bar_state: BarState,
        selection: SelectionResult,
    ) -> None:
        """
        Write on every new ClassificationResult (verbal stream event).
        This is the primary raw data source for Zone 3 mutation review.
        """
        await self._write({
            "event_type": "moment_event",
            "session_id": session_id,
            "moment_type": classification.moment_type.value,
            "confidence": round(classification.confidence, 3),
            "path": classification.path,
            "text_snippet": classification.text_snippet,
            "hook_score": bar_state.hook_score,
            "close_score": bar_state.close_score,
            "hook_trend": bar_state.hook_trend,
            "close_trend": bar_state.close_trend,
            "top_option": {
                "core_approach": selection.option_a.get("core_approach", ""),
                "base_probability": selection.option_a.get("base_probability", 50),
                "was_adapted": selection.was_adapted,
            },
        })

    async def log_periodic_snapshot(
        self,
        session_id: str,
        para: ParalinguisticSignals,
        bar_state: Optional[BarState],
        elapsed_seconds: float,
    ) -> None:
        """
        Write every 30 seconds. Captures paralinguistic state + bars.
        """
        snapshot: dict = {
            "event_type": "periodic_snapshot",
            "session_id": session_id,
            "elapsed_seconds": round(elapsed_seconds, 1),
            "paralinguistics": {
                "speech_rate_delta": round(para.speech_rate_delta, 3),
                "volume_level": round(para.volume_level, 3),
                "pause_duration": round(para.pause_duration, 2),
                "voice_tension_index": round(para.voice_tension_index, 3),
                "cadence_consistency_score": round(para.cadence_consistency_score, 3),
            },
        }

        if bar_state is not None:
            snapshot["bars"] = {
                "hook_score": bar_state.hook_score,
                "close_score": bar_state.close_score,
                "hook_trend": bar_state.hook_trend,
                "close_trend": bar_state.close_trend,
            }

        await self._write(snapshot)

    async def log_divergence_alert(self, alert) -> None:
        """
        Write when verbal and paralinguistic signals diverge.
        High-value event for Zone 3 — indicates masking / executive flex.
        """
        await self._write({
            "event_type": "divergence_alert",
            "session_id": self._session_id,
            "verbal_type": str(
                getattr(alert, "verbal_type", None)
                or getattr(alert, "verbal_moment_type", None)
            ),
            "alert_message": getattr(alert, "alert_message", ""),
            "practitioner_instruction": getattr(alert, "practitioner_instruction", ""),
            "severity": getattr(alert, "severity", "moderate"),
            "tension_index": getattr(alert, "tension_index", None),
            "speech_rate_delta": getattr(alert, "speech_rate_delta", None),
            "volume_level": getattr(alert, "volume_level", None),
        })

    async def log_option_choice(
        self,
        session_id: str,
        option_key: str,
        selection_result: SelectionResult,
        classification: Optional[ClassificationResult],
        bar_state: Optional[BarState],
    ) -> None:
        """
        Write when practitioner taps an option on the phone HUD.
        Captures which option they chose and the current session state.
        """
        chosen = getattr(selection_result, option_key, {})
        event: dict = {
            "event_type": "option_choice",
            "session_id": session_id,
            "option_key": option_key,
            "chosen_approach": chosen.get("core_approach", "") if isinstance(chosen, dict) else "",
            "chosen_language": chosen.get("base_language", "") if isinstance(chosen, dict) else "",
            "base_probability": chosen.get("base_probability", 0) if isinstance(chosen, dict) else 0,
            "was_adapted": selection_result.was_adapted,
        }

        if classification is not None:
            event["moment_type"] = classification.moment_type.value
            event["confidence"] = round(classification.confidence, 3)

        if bar_state is not None:
            event["hook_score"] = bar_state.hook_score
            event["close_score"] = bar_state.close_score

        await self._write(event)

    # ================================================================== #
    #  Internal                                                             #
    # ================================================================== #

    async def _write(self, event: dict) -> None:
        """
        Append one JSON event to the log file. Thread-safe via asyncio.Lock.
        Non-blocking — uses run_in_executor for file I/O.
        """
        event["_ts"] = datetime.now(timezone.utc).isoformat()
        self._event_count += 1

        if self._log_file is None:
            # Log not opened yet — write to structlog only
            logger.warning(
                "session_logger.not_opened",
                event_type=event.get("event_type"),
            )
            return

        line = json.dumps(event, default=self._json_default) + "\n"

        async with self._lock:
            try:
                await asyncio.get_event_loop().run_in_executor(
                    None, self._append_line, line
                )
            except Exception as e:
                logger.warning("session_logger.write_error", error=str(e))

    def _append_line(self, line: str) -> None:
        """Synchronous file append — called in executor."""
        with open(self._log_file, "a", encoding="utf-8") as f:
            f.write(line)

    @staticmethod
    def _json_default(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if hasattr(obj, "value"):   # Enums
            return obj.value
        return str(obj)
