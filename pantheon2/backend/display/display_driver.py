"""
Module: display_driver.py
Zone: 2 (Live session — no network, no cloud calls)
Input: BarState, SelectionResult, DivergenceAlert (optional)
Output: Rendered HUD state (device-specific)
LLM calls: 0
Side effects: Writes to device display / haptics
Latency tolerance: <50ms render budget within Zone 2 total <400ms

Abstract base class for all HUD display targets.
Concrete implementations: WatchDriver, PhoneDriver, GlassesDriver.

CONSTRAINT: All Zone 2 HUD rendering calls go through this abstraction.
Direct calls to watch/phone hardware APIs exist ONLY inside concrete drivers.
Per PRD CLAUDE.md Critical Constraint #3.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import structlog

from backend.bars.bar_calculator import BarState
from backend.dialog.dialog_selector import SelectionResult

logger = structlog.get_logger(__name__)


@dataclass
class HUDPayload:
    """
    The complete HUD update package assembled by the Zone 2 event loop
    and passed to whichever DisplayDriver is active.

    Both WatchDriver and PhoneDriver accept this same payload —
    each extracts what it can render given its screen real estate.
    """
    bar_state: BarState
    selection: SelectionResult
    session_elapsed_seconds: float
    divergence_alert: Optional[object] = None   # DivergenceAlert | None
    rwi_live: Any = 50                          # int | RWISnapshot — from VerbalObservedState
    timestamp: Optional[datetime] = None
    # NEW: Stream B paralinguistic signals — emitted in phone HiddenSignalPanel
    para: Optional[object] = None               # ParalinguisticSignals | None
    # NEW: Genome confidence badge — always present (PRD Critical Constraint #4)
    confidence_badge: Optional[object] = None   # ConfidenceBadgePayload | None

    def __post_init__(self) -> None:
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


class DisplayDriver(ABC):
    """
    Abstract base class for HUD display drivers.
    All Zone 2 rendering calls route through this interface.

    Subclasses implement:
      - render(payload): full HUD update
      - render_bars_only(bar_state): lightweight bar-only refresh
      - haptic(pattern): trigger haptic feedback
      - clear(): blank the display

    Zone 2 only. No cloud calls ever.
    """

    @abstractmethod
    def render(self, payload: HUDPayload) -> None:
        """
        Full HUD update. Called on every new SelectionResult.
        Must complete in <50ms to stay within Zone 2 budget.
        """

    @abstractmethod
    def render_bars_only(self, bar_state: BarState) -> None:
        """
        Lightweight bar refresh. Called when bars update but moment type
        has not changed (e.g., paralinguistic drift between classifications).
        """

    @abstractmethod
    def haptic(self, pattern: str) -> None:
        """
        Trigger haptic feedback.
        pattern: "single" | "double" | "long" — device-specific mapping.
        """

    @abstractmethod
    def clear(self) -> None:
        """Blank the display. Called on session end."""

    @property
    def driver_name(self) -> str:
        """Human-readable driver name for logging."""
        return self.__class__.__name__

    def log_render(self, payload: HUDPayload) -> None:
        """Shared logging helper — call from subclass render() implementations."""
        logger.debug(
            "display_driver.render",
            driver=self.driver_name,
            moment=payload.selection.moment_type,
            hook=payload.bar_state.hook_score,
            close=payload.bar_state.close_score,
            was_adapted=payload.selection.was_adapted,
        )
