"""
Module: phone_driver.py
Zone: 2 (Live session — no network, no cloud calls)
Input: HUDPayload
Output: Phone landscape HUD update (full HUD + HiddenSignalPanel)
LLM calls: 0
Side effects: Pushes HUD state to React Native HUDStateManager via local IPC/queue
Latency tolerance: <50ms

Phone landscape HUD — full information density.
What the phone shows:
  - Hook bar + Close bar (with trend arrows)
  - 3 dialog options (core_approach + base_language + probability bar)
  - RWI live indicator
  - Current moment type label
  - Confidence badge (ALWAYS shown per PRD CLAUDE.md Critical Constraint #4)
  - HiddenSignalPanel: paralinguistic stream (voice tension, rate, volume, pause)
    + DivergenceAlert if active

HiddenSignalPanel is visible to the practitioner in landscape mode —
it's "hidden" from the prospect, not from the practitioner.
It shows the raw paralinguistic signals so the practitioner can see what the
SLM is reacting to, building trust in the system.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

import structlog

from backend.bars.bar_calculator import BarState
from backend.display.display_driver import DisplayDriver, HUDPayload

logger = structlog.get_logger(__name__)


class PhoneDriver(DisplayDriver):
    """
    Phone landscape HUD driver.
    Renders full Zone 2 state: bars, 3 options, RWI, moment type, paralinguistics.
    Pushes structured payload to React Native HUDStateManager via state_emitter.

    Zone 2 only. No cloud calls.
    """

    def __init__(self, state_emitter=None) -> None:
        """
        Args:
            state_emitter: Optional emitter that sends HUD state to the React Native layer.
                           If None, stubs by logging the payload.
        """
        self._emitter = state_emitter

    def render(self, payload: HUDPayload) -> None:
        """
        Full phone HUD update. Builds complete state dict and emits.
        """
        self.log_render(payload)

        hud_state = self._build_hud_state(payload)
        self._emit(hud_state)

    def render_bars_only(self, bar_state: BarState) -> None:
        """
        Lightweight bar-only refresh. Partial state update.
        TypeScript HUDStateManager detects single-key payload and calls updateBarsOnly().
        """
        partial = {
            "bars": {
                "hook_score": bar_state.hook_score,   # TypeScript BarState.hook_score
                "close_score": bar_state.close_score, # TypeScript BarState.close_score
                "hook_trend": bar_state.hook_trend,
                "close_trend": bar_state.close_trend,
            }
        }
        self._emit(partial)

    def haptic(self, pattern: str) -> None:
        """Phone haptic — forwarded to emitter if available."""
        if self._emitter is not None:
            try:
                self._emitter.haptic(pattern)
            except Exception as e:
                logger.warning("phone_driver.haptic_error", pattern=pattern, error=str(e))
        else:
            logger.debug("phone_driver.haptic_stub", pattern=pattern)

    def clear(self) -> None:
        """Clear the phone HUD. Called on session end."""
        self._emit({"_session_ended": True})
        logger.info("phone_driver.cleared")

    # ------------------------------------------------------------------ #
    # Private helpers                                                       #
    # ------------------------------------------------------------------ #

    def _build_hud_state(self, payload: HUDPayload) -> dict[str, Any]:
        """
        Assembles the complete HUD state dict emitted to React Native HUDStateManager.
        Field names MUST match mobile/src/types/index.ts HUDState exactly.
        """
        # ── Bars ─────────────────────────────────────────────────────────
        bars = {
            "hook_score": payload.bar_state.hook_score,    # TypeScript BarState.hook_score
            "close_score": payload.bar_state.close_score,  # TypeScript BarState.close_score
            "hook_trend": payload.bar_state.hook_trend,
            "close_trend": payload.bar_state.close_trend,
        }

        # ── RWI — emit as object (TypeScript: { score, window_status }) ──
        rwi_raw = payload.rwi_live
        if hasattr(rwi_raw, "score") and hasattr(rwi_raw, "window_status"):
            rwi_live = {
                "score": rwi_raw.score,
                "window_status": rwi_raw.window_status,
            }
        elif isinstance(rwi_raw, dict):
            rwi_live = {
                "score": rwi_raw.get("score", 50),
                "window_status": rwi_raw.get("window_status", "open"),
            }
        else:
            # Legacy: rwi_live was a plain int — derive window_status
            score = int(rwi_raw) if rwi_raw is not None else 50
            if score >= 80:
                status = "peak"
            elif score >= 60:
                status = "open"
            elif score >= 31:
                status = "narrowing"
            else:
                status = "closed"
            rwi_live = {"score": score, "window_status": status}

        # ── Confidence badge — ALWAYS present (PRD Critical Constraint #4) ─
        cb = payload.confidence_badge
        if cb is not None:
            confidence_badge = {
                "level": cb.level,
                "label": cb.label,
                "color": cb.color,
            }
        else:
            confidence_badge = {"level": "MEDIUM", "label": "Medium Confidence", "color": "yellow"}

        # ── Selection (TypeScript SelectionResult) ────────────────────────
        sel = payload.selection
        selection = {
            "moment_type": getattr(sel, "moment_type", ""),
            "option_a": self._format_option(getattr(sel, "option_a", {})),
            "option_b": self._format_option(getattr(sel, "option_b", {})),
            "option_c": self._format_option(getattr(sel, "option_c", {})),
            "was_adapted": getattr(sel, "was_adapted", False),
            "is_cache_fallback": getattr(sel, "is_cache_fallback", False),
            "classification_confidence": getattr(sel, "classification_confidence", 0.5),
        }

        # ── Paralinguistics (Stream B) — Python field names ───────────────
        para = None
        if payload.para is not None:
            p = payload.para
            para = {
                "speech_rate_delta": getattr(p, "speech_rate_delta", 0.0),
                "volume_level": getattr(p, "volume_level", 0.5),
                "pause_duration": getattr(p, "pause_duration", 0.0),
                "voice_tension_index": getattr(p, "voice_tension_index", 0.0),
                "cadence_consistency_score": getattr(p, "cadence_consistency_score", 1.0),
            }

        # ── Divergence alert (top-level, not nested) ──────────────────────
        divergence_alert = None
        if payload.divergence_alert is not None:
            alert = payload.divergence_alert
            divergence_alert = {
                "active": True,
                "severity": getattr(alert, "severity", "moderate").upper(),
                "description": getattr(alert, "alert_message", ""),
                "verbal_state": getattr(alert, "verbal_description", ""),
                "para_state": getattr(alert, "paralinguistic_description", ""),
                "recommendation": getattr(alert, "practitioner_instruction", ""),
                "verbal_type": getattr(alert, "verbal_moment_type", None),
                "alert_message": getattr(alert, "alert_message", ""),
            }

        # ── Elapsed ───────────────────────────────────────────────────────
        elapsed = payload.session_elapsed_seconds

        return {
            "bars": bars,
            "moment_type": getattr(sel, "moment_type", "neutral_exploratory"),
            "classification_confidence": getattr(sel, "classification_confidence", 0.5),
            "confidence_badge": confidence_badge,
            "rwi_live": rwi_live,
            "selection": selection,
            "para": para,
            "divergence_alert": divergence_alert,
            "elapsed_seconds": elapsed,           # TypeScript: HUDState.elapsed_seconds
            "selected_key": None,
            "timestamp": payload.timestamp.isoformat() if payload.timestamp else None,
        }

    def _format_option(self, option: dict) -> dict:
        """Extract display-relevant fields from an option dict."""
        if not isinstance(option, dict):
            return {}
        return {
            "core_approach": option.get("core_approach", ""),
            "base_language": option.get("base_language", ""),
            "trigger_phrase": option.get("trigger_phrase", ""),
            "base_probability": option.get("base_probability", 50),
        }

    def _emit(self, state: dict) -> None:
        """Send state to emitter. Stub-logs if no emitter attached."""
        if self._emitter is not None:
            try:
                self._emitter.emit(state)
            except Exception as e:
                logger.warning("phone_driver.emit_error", error=str(e))
        else:
            logger.debug("phone_driver.emit_stub", keys=list(state.keys()))
