"""
Module: parameter_definitions.py
Zone: Foundation (imported by all zones)
Input: N/A — pure definitions
Output: Pydantic models for Genome, all 18 parameters, confidence, mutation log
LLM calls: 0
Side effects: None
Latency tolerance: N/A (import-time only)

This file is the single source of truth for all genome data shapes.
Do NOT define genome structure anywhere else.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator


# ================================================================== #
#  ENUMS                                                               #
# ================================================================== #

class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"       # Supabase genome, age < 90 days, 1+ mutation entry
    MEDIUM = "MEDIUM"   # Fresh scrape
    LOW = "LOW"         # Manual intake form only


class MutationStrength(str, Enum):
    WEAK = "WEAK"           # Single observation — monitor only
    MODERATE = "MODERATE"   # 2 observations, same direction
    STRONG = "STRONG"       # 3+ observations, 2+ contexts


class MutationDecision(str, Enum):
    APPROVED = "APPROVED"
    REJECTED_GATE = "REJECTED_GATE"         # Did not pass velocity gate
    REJECTED_COHERENCE = "REJECTED_COHERENCE"  # Contradicts Formation Layer invariant
    PENDING_HUMAN = "PENDING_HUMAN"         # Awaiting practitioner confirmation


class MomentType(str, Enum):
    NEUTRAL_EXPLORATORY = "neutral_exploratory"
    IRATE_RESISTANT = "irate_resistant"
    TOPIC_AVOIDANCE = "topic_avoidance"
    IDENTITY_THREAT = "identity_threat"
    HIGH_OPENNESS = "high_openness"
    CLOSING_SIGNAL = "closing_signal"


class SessionOutcome(str, Enum):
    CLOSE_YES = "close_yes"
    CLOSE_NO = "close_no"
    FOLLOW_UP = "follow_up"
    INCOMPLETE = "incomplete"


class DeltaSignalType(str, Enum):
    VALIDATION_EVENT = "validation_event"
    FRICTION_SIGNAL = "friction_signal"
    IDENTITY_MOMENTUM = "identity_momentum"
    CONSOLIDATION = "consolidation"
    NEUTRAL = "neutral"


# ================================================================== #
#  GENOME — 18 PARAMETERS                                             #
# ================================================================== #

def _score(description: str) -> Field:
    """Helper: INT 1–100 field factory with description."""
    return Field(..., ge=1, le=100, description=description)


class GenomeScores(BaseModel):
    """
    The 18-parameter personality genome. All scores INT 1–100.
    Derived from behavioral evidence only — never assigned arbitrarily.

    Cluster A — Classic Personality (OCEAN-derived)
    Cluster B — Behavioral and Cultural
    Cluster C — Cognitive Architecture (Human Uniqueness Dimensions)
    """

    # --- Cluster A: OCEAN-derived ---
    openness: int = _score(
        "Willingness to engage novel ideas. "
        "High: receptive to reframing. Low: needs familiar frameworks."
    )
    conscientiousness: int = _score(
        "Planning and follow-through. "
        "High: needs process clarity before committing. Low: moved by momentum."
    )
    extraversion: int = _score(
        "Social energy. Calibrates probe question pacing and silence tolerance."
    )
    agreeableness: int = _score(
        "Baseline cooperativeness. "
        "High: may over-agree without real commitment. Low: expects challenge."
    )
    neuroticism: int = _score(
        "Anxiety and risk sensitivity. "
        "High: needs safety signals, exit options. Low: handles pressure."
    )

    # --- Cluster B: Behavioral and Cultural ---
    communication_style: int = _score(
        "How explicitly the person states intent. "
        "1=indirect, 100=direct. Critical for opener length and confrontation tolerance."
    )
    decision_making: int = _score(
        "Evidence vs intuition. High: lead with data. Low: lead with vision/narrative."
    )
    brand_relationship: int = _score(
        "Loyalty vs cost sensitivity. High: position as premium. Low: lead with ROI."
    )
    influence_susceptibility: int = _score(
        "Openness to social proof. High: peer endorsement is powerful."
    )
    emotional_expression: int = _score(
        "How much emotion surfaces publicly. "
        "Low: read micro-signals, not verbal cues. High: verbal feedback is reliable."
    )
    conflict_behavior: int = _score(
        "How the person handles disagreement. "
        "Determines which dialog options are safe under irate moments."
    )
    literacy_and_articulation: int = _score(
        "Vocabulary and reasoning sophistication. "
        "Calibrates language register of all communication."
    )
    socioeconomic_friction: int = _score(
        "Systemic barriers and financial precarity. "
        "Derived from genome signals — never from private disclosure."
    )

    # --- Cluster C: Human Uniqueness Dimensions ---
    identity_fusion: int = _score(
        "How much group identity overrides personal utility. "
        "High: frame proposition as community benefit. Low: personal edge."
    )
    chronesthesia_capacity: int = _score(
        "Mental time travel — ability to project decisions into future consequences. "
        "High: vision hooks. Low: immediate pain hooks."
    )
    tom_self_awareness: int = _score(
        "Accuracy of self-knowledge. "
        "High: they know what they want. Low: surface needs may mask real needs."
    )
    tom_social_modeling: int = _score(
        "Ability to model others' perceptions. "
        "High: will read your pitch — be authentic. Low: standard approach works."
    )
    executive_flexibility: int = _score(
        "Ability to override base traits in professional contexts. "
        "High: surface behavior is performance, not reality. Low: surface is genuine."
    )

    @field_validator(
        "openness", "conscientiousness", "extraversion", "agreeableness",
        "neuroticism", "communication_style", "decision_making", "brand_relationship",
        "influence_susceptibility", "emotional_expression", "conflict_behavior",
        "literacy_and_articulation", "socioeconomic_friction", "identity_fusion",
        "chronesthesia_capacity", "tom_self_awareness", "tom_social_modeling",
        "executive_flexibility",
        mode="before",
    )
    @classmethod
    def clamp_score(cls, v: int) -> int:
        return max(1, min(100, int(v)))


# ================================================================== #
#  GENOME RECORD (full database row)                                  #
# ================================================================== #

class Genome(GenomeScores):
    """Full genome record as stored in Supabase."""
    genome_id: Optional[str] = None
    prospect_id: str
    confidence: ConfidenceLevel
    last_scraped_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # Formation Layer invariants — traits considered deeply stable
    # (set during genome build from earliest biographical signals)
    formation_invariants: list[str] = Field(
        default_factory=list,
        description="Trait names considered Formation Layer invariants. "
                    "Mutations to these are flagged as COHERENCE_TENSION.",
    )

    model_config = {"from_attributes": True}


# ================================================================== #
#  MUTATION LOG                                                        #
# ================================================================== #

class MutationCandidate(BaseModel):
    """
    A candidate trait change surfaced by Zone 3 analysis.
    Must pass the velocity gate AND human confirmation before becoming a MutationLogEntry.
    """
    prospect_id: str
    trait_name: str
    current_score: int
    suggested_delta: int       # Positive = score rises, negative = falls
    suggested_new_score: int
    evidence: list[str]        # Descriptions of supporting observations
    strength: MutationStrength
    is_coherence_tension: bool = False  # True if contradicts Formation Layer invariant
    session_ids: list[str] = Field(default_factory=list)


class MutationLogEntry(BaseModel):
    """A confirmed and gate-approved genome mutation. Written to Supabase."""
    log_id: Optional[str] = None
    prospect_id: str
    trait_name: str
    old_score: int
    new_score: int
    delta: int
    confirmed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    confirmed_by: str          # practitioner_id
    evidence_summary: str
    gate_observations_count: int
    gate_contexts_count: int
    gate_day_span: int

    model_config = {"from_attributes": True}


# ================================================================== #
#  OBSERVED STATE                                                      #
# ================================================================== #

class VerbalObservedState(BaseModel):
    """
    Session-scoped. Verbal signals from Stream A (transcript).
    Resets completely after every session. Never writes to genome.
    """
    session_id: str
    current_moment_type: MomentType = MomentType.NEUTRAL_EXPLORATORY
    sentiment_score: float = Field(0.0, ge=-1.0, le=1.0)  # -1=negative, +1=positive
    readiness_level: int = Field(50, ge=0, le=100)
    topic_avoidance_flags: list[str] = Field(default_factory=list)
    hook_bar: int = Field(50, ge=0, le=100)
    close_bar: int = Field(50, ge=0, le=100)
    rwi_live: int = Field(50, ge=0, le=100)
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ParalinguisticObservedState(BaseModel):
    """
    Session-scoped. Signals from Stream B (raw audio features).
    Resets completely after every session.
    Baseline established from first 90 seconds of session (basa-basi phase).
    """
    session_id: str
    # Baseline (established in first 90s)
    baseline_speech_rate: Optional[float] = None   # syllables/second
    baseline_volume: Optional[float] = None         # normalized 0–1
    baseline_cadence_variance: Optional[float] = None

    # Live values (delta from baseline where applicable)
    speech_rate_delta: float = 0.0      # % change from baseline (+ve = faster)
    volume_level: float = Field(0.5, ge=0.0, le=1.0)
    pause_duration_last: float = 0.0    # seconds of last silence after practitioner spoke
    voice_tension_index: float = Field(0.0, ge=0.0, le=1.0)  # 0=relaxed, 1=tense
    cadence_consistency_score: float = Field(1.0, ge=0.0, le=1.0)  # 1=consistent
    baseline_established: bool = False
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DivergenceAlert(BaseModel):
    """Fired when verbal (Stream A) and paralinguistic (Stream B) signals contradict."""
    session_id: str
    fired_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    verbal_moment_type: MomentType
    verbal_description: str
    paralinguistic_description: str
    alert_message: str              # Human-readable. Shown in HiddenSignalPanel.
    severity: str = "moderate"      # "low" | "moderate" | "high"


class ObservedState(BaseModel):
    """Combined observed state. Both streams together."""
    verbal: VerbalObservedState
    paralinguistic: ParalinguisticObservedState
    active_divergence_alert: Optional[DivergenceAlert] = None

    # Delta signals injected pre-session from signal_delta pipeline
    delta_signals: list["DeltaSignal"] = Field(default_factory=list)


# ================================================================== #
#  SIGNAL DELTA                                                        #
# ================================================================== #

class DeltaSignal(BaseModel):
    """
    A new social signal found since last_scrape_timestamp.
    Writes to Observed State only — never to genome traits.
    """
    prospect_id: str
    signal_type: DeltaSignalType
    source: str                  # "linkedin" | "instagram"
    detected_at: datetime
    content_summary: str         # Brief description of the post/event
    rwi_impact: int              # Estimated RWI delta (positive or negative)
    display_message: str         # Shown on pre-session screen, e.g. "Promotion post 4 days ago → RWI +12"


# ================================================================== #
#  RWI                                                                 #
# ================================================================== #

class RWIComponents(BaseModel):
    validation_recency: int = Field(50, ge=0, le=100)
    friction_saturation: int = Field(50, ge=0, le=100)
    decision_fatigue_estimate: int = Field(50, ge=0, le=100)
    identity_momentum: int = Field(50, ge=0, le=100)


class RWISnapshot(BaseModel):
    prospect_id: str
    score: int = Field(..., ge=0, le=100)
    components: RWIComponents
    window_status: str  # "closed" | "narrowing" | "open" | "peak"
    strategy_note: str
    computed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("window_status", mode="before")
    @classmethod
    def derive_window_status(cls, v: str) -> str:
        # Allow pre-set value (used in tests)
        return v


def rwi_window_status(score: int) -> tuple[str, str]:
    """Returns (window_status, strategy_note) for a given RWI score."""
    if score <= 30:
        return "closed", "Seed only. Build relationship. No commitment ask."
    elif score <= 59:
        return "narrowing", "Trust-building and pain-surfacing. Do not force acceleration."
    elif score <= 79:
        return "open", "Vision framing. Advance to commitment-anchoring options."
    else:
        return "peak", "Direct close with specific next step. Window is temporary."


# ================================================================== #
#  GENOME BUNDLE (resolver output)                                    #
# ================================================================== #

class GenomeBundle(BaseModel):
    """Output of genome_resolver.py — everything needed to start a session."""
    genome: Genome
    confidence: ConfidenceLevel
    rwi: Optional[RWISnapshot] = None
    delta_signals: list[DeltaSignal] = Field(default_factory=list)
    resolver_path: str = ""  # "supabase" | "fresh_scrape" | "intake_form"
