"""
Module: watch_driver.py
Zone: 2 (Live session — no network, no cloud calls)
Input: HUDPayload
Output: Watch face update (bars + 3-word trigger phrase + haptic)
LLM calls: 0
Side effects: Sends render commands to WatchOS/WearOS bridge (stubbed until hardware connected)
Latency tolerance: <50ms

Smartwatch HUD — minimal information, maximum signal density.
What the watch shows:
  - Hook bar (0–100, graphical)
  - Close bar (0–100, graphical)
  - 3-word trigger phrase from highest-probability option
  - Haptic on: moment type changes, DivergenceAlert, close bar >70

Display philosophy (PRD 2.3):
  The watch is the practitioner's peripheral signal.
  It must not demand attention — just register subconsciously.
  Three words max. No sentences. No probability numbers on watch.
"""

from __future__ import annotations

import structlog

from backend.bars.bar_calculator import BarState
from backend.display.display_driver import DisplayDriver, HUDPayload

logger = structlog.get_logger(__name__)

# Haptic patterns (mapped to actual watch APIs in hardware integration layer)
HAPTIC_SINGLE = "single"
HAPTIC_DOUBLE = "double"
HAPTIC_LONG = "long"

# Thresholds for auto-haptic events
CLOSE_BAR_HAPTIC_THRESHOLD = 70     # Close bar rising above this → double haptic
DIVERGENCE_HAPTIC_PATTERN = HAPTIC_LONG


class WatchDriver(DisplayDriver):
    """
    Smartwatch HUD driver.
    Renders: hook bar, close bar, 3-word trigger phrase.
    Fires haptics on: moment type change, divergence alert, close bar peak.

    Zone 2 only. No cloud calls.
    """

    def __init__(self, watch_bridge=None) -> None:
        """
        Args:
            watch_bridge: Optional hardware bridge instance.
                          Stub if None — logs calls without sending to hardware.
        """
        self._bridge = watch_bridge
        self._last_moment_type: str = ""
        self._last_close_score: int = 0

    def render(self, payload: HUDPayload) -> None:
        """
        Full watch face update. Extracts 3-word trigger from top option.
        Fires haptic if: moment type changed | divergence alert present | close >70.
        """
        self.log_render(payload)

        trigger = self._extract_trigger_phrase(payload.selection)
        hook = payload.bar_state.hook_score
        close = payload.bar_state.close_score

        watch_state = {
            "hook": hook,
            "close": close,
            "trigger": trigger,        # 3 words max
            "hook_trend": payload.bar_state.hook_trend,
            "close_trend": payload.bar_state.close_trend,
        }

        self._send(watch_state)

        # Auto-haptic logic
        self._maybe_haptic(payload)

        # Track state for delta detection
        self._last_moment_type = payload.selection.moment_type
        self._last_close_score = close

    def render_bars_only(self, bar_state: BarState) -> None:
        """
        Lightweight bar refresh — no trigger phrase update.
        Called during paralinguistic drift between moment type changes.
        """
        watch_state = {
            "hook": bar_state.hook_score,
            "close": bar_state.close_score,
            "hook_trend": bar_state.hook_trend,
            "close_trend": bar_state.close_trend,
        }
        self._send(watch_state)

    def haptic(self, pattern: str) -> None:
        """Send haptic to watch. Patterns: 'single' | 'double' | 'long'."""
        if self._bridge is not None:
            try:
                self._bridge.haptic(pattern)
            except Exception as e:
                logger.warning("watch_driver.haptic_error", pattern=pattern, error=str(e))
        else:
            logger.debug("watch_driver.haptic_stub", pattern=pattern)

    def clear(self) -> None:
        """Blank the watch face. Called on session end."""
        self._send({"hook": 0, "close": 0, "trigger": "---"})
        self._last_moment_type = ""
        self._last_close_score = 0
        logger.info("watch_driver.cleared")

    # ------------------------------------------------------------------ #
    # Private helpers                                                       #
    # ------------------------------------------------------------------ #

    def _extract_trigger_phrase(self, selection) -> str:
        """
        Extract the trigger_phrase from the highest-probability option.
        Falls back through option_a → option_b → option_c → default.
        Truncates to 3 words max per watch display contract.
        """
        best_option = None
        best_prob = -1

        for key in ("option_a", "option_b", "option_c"):
            opt = getattr(selection, key, {})
            if isinstance(opt, dict):
                prob = opt.get("base_probability", 0)
                if prob > best_prob:
                    best_prob = prob
                    best_option = opt

        if best_option is None:
            return "Stay present"

        phrase = best_option.get("trigger_phrase", "")
        if not phrase:
            # Fall back to first 3 words of base_language
            words = best_option.get("base_language", "Stay present").split()
            phrase = " ".join(words[:3])

        # Enforce 3-word limit
        words = phrase.split()
        return " ".join(words[:3])

    def _maybe_haptic(self, payload: HUDPayload) -> None:
        """Fire haptics for significant events."""
        # Moment type changed → single tap
        if payload.selection.moment_type != self._last_moment_type and self._last_moment_type:
            self.haptic(HAPTIC_SINGLE)

        # DivergenceAlert active → long vibration (practitioner needs to notice)
        if payload.divergence_alert is not None:
            self.haptic(DIVERGENCE_HAPTIC_PATTERN)

        # Close bar crossing peak threshold → double tap
        close = payload.bar_state.close_score
        if close >= CLOSE_BAR_HAPTIC_THRESHOLD > self._last_close_score:
            self.haptic(HAPTIC_DOUBLE)

    def _send(self, state: dict) -> None:
        """Send state dict to watch bridge. Stub-logs if no bridge attached."""
        if self._bridge is not None:
            try:
                self._bridge.send(state)
            except Exception as e:
                logger.warning("watch_driver.send_error", error=str(e))
        else:
            logger.debug("watch_driver.send_stub", state=state)
