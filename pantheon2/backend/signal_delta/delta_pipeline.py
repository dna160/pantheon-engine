"""
Module: delta_pipeline.py  — FACADE (import shim)
Zone: 1 (Pre-session)

This file is the public entry point for the signal delta pipeline.
It re-exports the three classes split into their own modules per the
guide spec, and provides the run_signal_delta_pipeline() convenience
function used by harness_runner.py.

Existing imports of:
  from backend.signal_delta.delta_pipeline import run_signal_delta_pipeline
  from backend.signal_delta.delta_pipeline import DeltaScraper / DeltaClassifier / ObservedStateInjector
...continue to work unchanged.
"""

from __future__ import annotations

from datetime import datetime

import structlog

from backend.genome.parameter_definitions import DeltaSignal
from backend.signal_delta.delta_scraper import DeltaScraper
from backend.signal_delta.delta_classifier import DeltaClassifier
from backend.signal_delta.observed_state_injector import ObservedStateInjector

__all__ = [
    "DeltaScraper",
    "DeltaClassifier",
    "ObservedStateInjector",
    "run_signal_delta_pipeline",
]

logger = structlog.get_logger(__name__)


async def run_signal_delta_pipeline(
    prospect_id: str,
    session_id: str,
    last_scrape_timestamp: datetime | None,
    base_rwi: int,
) -> tuple[list[DeltaSignal], int]:
    """
    Convenience function that runs the full delta pipeline:
    scrape → classify → return (signals, adjusted_rwi).

    Observed State injection happens in session_init.py after this returns.
    Returns ([], base_rwi) on any failure — delta is always optional.
    """
    try:
        scraper = DeltaScraper()
        classifier = DeltaClassifier()

        raw = await scraper.scrape_since(prospect_id, last_scrape_timestamp)

        delta_signals: list[DeltaSignal] = []

        for post in raw.get("linkedin_posts", []):
            sig = classifier.classify(prospect_id, post, "linkedin")
            if sig:
                delta_signals.append(sig)

        for post in raw.get("instagram_posts", []):
            sig = classifier.classify(prospect_id, post, "instagram")
            if sig:
                delta_signals.append(sig)

        # Compute adjusted RWI from signals
        adjusted_rwi = base_rwi
        for sig in delta_signals:
            adjusted_rwi = max(0, min(100, adjusted_rwi + sig.rwi_impact))

        logger.info(
            "signal_delta_pipeline.complete",
            prospect_id=prospect_id,
            signals_found=len(delta_signals),
            base_rwi=base_rwi,
            adjusted_rwi=adjusted_rwi,
        )
        return delta_signals, adjusted_rwi

    except Exception as e:
        logger.error("signal_delta_pipeline.error", error=str(e))
        return [], base_rwi
