"""
Module: session_models.py
Zone: Foundation (imported by Zone 1, 2, and 3)
Input: N/A — pure Pydantic models
Output: SessionRecord, SessionEvent, ParalinguisticSnapshot data shapes
LLM calls: 0
Side effects: None
Latency tolerance: N/A (import-time only)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field
from backend.genome.parameter_definitions import MomentType, SessionOutcome


class SessionRecord(BaseModel):
    """Persisted session row. Created in Zone 1, closed in Zone 3."""
    session_id: str
    practitioner_id: str
    prospect_id: str
    genome_confidence: str        # HIGH | MEDIUM | LOW
    rwi_at_start: int             # RWI score at session start
    outcome: Optional[str] = None # filled on session close
    opened_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    closed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class SessionEvent(BaseModel):
    """
    A single session event — moment type change, practitioner option choice,
    or 30-second snapshot. Written by session_logger.py in Zone 2.
    Non-blocking writes only — never await in Zone 2.
    """
    event_id: Optional[str] = None
    session_id: str
    event_type: str               # "moment_change" | "option_chosen" | "snapshot" | "divergence_alert"
    event_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    moment_type: Optional[str] = None
    option_chosen: Optional[str] = None   # "option_a" | "option_b" | "option_c"
    hook_bar: Optional[int] = None        # 0–100
    close_bar: Optional[int] = None       # 0–100
    rwi_live: Optional[int] = None        # 0–100
    notes: Optional[str] = None

    model_config = {"from_attributes": True}


class ParalinguisticSnapshot(BaseModel):
    """
    30-second paralinguistic state snapshot written in Zone 2.
    Used by Zone 3 session_analyzer for pattern detection.
    Never stored in genome — session-scoped only.
    """
    snapshot_id: Optional[str] = None
    session_id: str
    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    speech_rate_delta: float = 0.0        # % from baseline
    volume_level: float = 0.5             # normalized 0–1
    pause_duration_last: float = 0.0      # seconds
    voice_tension_index: float = 0.0      # 0=relaxed, 1=tense
    cadence_consistency_score: float = 1.0
    baseline_established: bool = False
    divergence_active: bool = False

    model_config = {"from_attributes": True}
