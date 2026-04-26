"""
Module: glasses_driver.py
Zone: 2 (Live session — no network, no cloud calls)
Input: HUDPayload
Output: None (stub — logs calls only)
LLM calls: 0
Side effects: None (stub)
Latency tolerance: N/A (stub — returns immediately)

Smart glasses display driver — STUB for v2.
Per PRD CLAUDE.md: "GlassesDriver: stub (v2)"

This class fulfills the DisplayDriver interface so the Zone 2 event loop
can accept any DisplayDriver implementation without conditional logic.
All method calls are logged but no hardware rendering occurs.

When smart glasses hardware integration is ready in v2, this stub
will be replaced with actual AR display rendering logic.
"""

from __future__ import annotations

import structlog

from backend.bars.bar_calculator import BarState
from backend.display.display_driver import DisplayDriver, HUDPayload

logger = structlog.get_logger(__name__)


class GlassesDriver(DisplayDriver):
    """
    Smart glasses HUD driver — stub only.
    Logs all calls without rendering. Used in v2 hardware integration.
    Zone 2 only. No cloud calls.
    """

    def render(self, payload: HUDPayload) -> None:
        """Stub: logs render call without sending to hardware."""
        logger.debug(
            "glasses_driver.render_stub",
            moment=payload.selection.moment_type,
            hook=payload.bar_state.hook_score,
            close=payload.bar_state.close_score,
            note="Glasses hardware not connected — stub mode",
        )

    def render_bars_only(self, bar_state: BarState) -> None:
        """Stub: logs bar update without sending to hardware."""
        logger.debug(
            "glasses_driver.render_bars_stub",
            hook=bar_state.hook_score,
            close=bar_state.close_score,
            note="Glasses hardware not connected — stub mode",
        )

    def haptic(self, pattern: str) -> None:
        """Stub: smart glasses haptic not implemented in v1."""
        logger.debug("glasses_driver.haptic_stub", pattern=pattern)

    def clear(self) -> None:
        """Stub: logs clear call."""
        logger.debug("glasses_driver.clear_stub")
