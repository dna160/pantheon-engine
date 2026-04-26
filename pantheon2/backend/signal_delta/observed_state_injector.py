"""
Module: observed_state_injector.py
Zone: 1 (Pre-session — final step of signal delta pipeline)
Input: ObservedState, list[DeltaSignal], base_rwi int
Output: (ObservedState, adjusted_rwi int)
LLM calls: 0
Side effects: Mutates observed_state.delta_signals and verbal.rwi_live in-place
Latency tolerance: <10ms (pure arithmetic)

CRITICAL: This module NEVER writes to the genome. Observed State ONLY.
Delta signals reset with Observed State at session end.
Part of the Signal Delta pipeline. Imported by delta_pipeline.py facade.
"""

from __future__ import annotations

import structlog

from backend.genome.parameter_definitions import (
    DeltaSignal,
    ObservedState,
)

logger = structlog.get_logger(__name__)


class ObservedStateInjector:
    """
    Takes classified delta signals and injects their RWI impact
    into the Observed State before session start.

    CRITICAL: This NEVER writes to the genome. Observed State ONLY.
    Delta signals reset with Observed State at session end.
    """

    def inject(
        self,
        observed_state: ObservedState,
        delta_signals: list[DeltaSignal],
        base_rwi: int,
    ) -> tuple[ObservedState, int]:
        """
        Returns (updated_observed_state, adjusted_rwi_score).
        Adjusts rwi_live in verbal state based on delta signal impacts.
        """
        observed_state.delta_signals = delta_signals

        adjusted_rwi = base_rwi
        for signal in delta_signals:
            adjusted_rwi = max(0, min(100, adjusted_rwi + signal.rwi_impact))

        observed_state.verbal.rwi_live = adjusted_rwi

        logger.info(
            "observed_state_injector.injected",
            delta_count=len(delta_signals),
            base_rwi=base_rwi,
            adjusted_rwi=adjusted_rwi,
        )
        return observed_state, adjusted_rwi
