"""
Module: genome_writer.py
Zone: 3 (Post-session only)
Input: MutationCandidate, practitioner_id, Genome, list[MutationLogEntry]
Output: MutationDecision, optional MutationLogEntry
LLM calls: 0
Side effects: Writes to Supabase ONLY if all gate conditions pass AND human confirms
Latency tolerance: Async post-session. No latency constraint.

THE MUTATION GATE — THIS IS THE MOST CRITICAL INTEGRITY MECHANISM IN PANTHEON 2.0.
It is hardcoded. It has no bypass. It has no admin override.
A genome trait ONLY updates when ALL of the following are true:
  1. 3+ independent observations pointing in the same direction
  2. Across 2+ separate contexts
  3. Over a span of at least 21 days
  4. With at least 1 cold-context signal (not just in-session behavior)
  5. Human practitioner has explicitly confirmed the mutation

If ANY condition fails, the mutation is REJECTED and the genome is NOT updated.
The candidate is archived for future accumulation.

Rationale: Single-session behavioral signals are poor proxies for stable traits.
(Fleeson 2001 — trait as density distribution, not fixed state.)
"""

from __future__ import annotations

from datetime import datetime, timezone
import structlog

from backend.genome.parameter_definitions import (
    Genome,
    MutationCandidate,
    MutationDecision,
    MutationLogEntry,
    MutationStrength,
)
from backend.db.genome_repo import GenomeRepo

logger = structlog.get_logger(__name__)

# Gate thresholds — DO NOT CHANGE without PRD approval
GATE_MIN_OBSERVATIONS = 3
GATE_MIN_CONTEXTS = 2
GATE_MIN_DAY_SPAN = 21
GATE_REQUIRES_COLD_CONTEXT = True  # At least one non-session signal


class MutationGateResult(Exception):
    """Raised when gate check produces a rejection — used as control flow."""
    def __init__(self, decision: MutationDecision, reason: str):
        self.decision = decision
        self.reason = reason
        super().__init__(reason)


def validate_mutation_gate(
    candidate: MutationCandidate,
    existing_log: list[MutationLogEntry],
    has_cold_context_signal: bool,
    observation_day_span: int,
    context_count: int,
) -> MutationDecision:
    """
    Validates all gate conditions for a mutation candidate.
    Returns MutationDecision.APPROVED only if ALL conditions pass.

    Args:
        candidate: The mutation being proposed
        existing_log: All prior confirmed mutations for this prospect + trait
        has_cold_context_signal: True if at least one observation came from
                                  outside a live session (e.g. LinkedIn change,
                                  post-session behavioral evidence)
        observation_day_span: Number of days spanning the supporting observations
        context_count: Number of distinct contexts (sessions, channels) that
                        produced observations

    Returns:
        MutationDecision enum value
    """
    # --- Gate 1: Minimum observations ---
    if len(candidate.evidence) < GATE_MIN_OBSERVATIONS:
        logger.warning(
            "mutation_gate.rejected.insufficient_observations",
            trait=candidate.trait_name,
            count=len(candidate.evidence),
            required=GATE_MIN_OBSERVATIONS,
        )
        return MutationDecision.REJECTED_GATE

    # --- Gate 2: Minimum contexts ---
    if context_count < GATE_MIN_CONTEXTS:
        logger.warning(
            "mutation_gate.rejected.insufficient_contexts",
            trait=candidate.trait_name,
            contexts=context_count,
            required=GATE_MIN_CONTEXTS,
        )
        return MutationDecision.REJECTED_GATE

    # --- Gate 3: Minimum day span ---
    if observation_day_span < GATE_MIN_DAY_SPAN:
        logger.warning(
            "mutation_gate.rejected.insufficient_day_span",
            trait=candidate.trait_name,
            days=observation_day_span,
            required=GATE_MIN_DAY_SPAN,
        )
        return MutationDecision.REJECTED_GATE

    # --- Gate 4: Cold context signal required ---
    if GATE_REQUIRES_COLD_CONTEXT and not has_cold_context_signal:
        logger.warning(
            "mutation_gate.rejected.no_cold_context",
            trait=candidate.trait_name,
        )
        return MutationDecision.REJECTED_GATE

    # --- Gate 5: Coherence tension check ---
    # (formation invariants passed in via candidate.is_coherence_tension)
    if candidate.is_coherence_tension:
        logger.warning(
            "mutation_gate.rejected.coherence_tension",
            trait=candidate.trait_name,
            note="Contradicts Formation Layer invariant. Not written. Flagged for review.",
        )
        return MutationDecision.REJECTED_COHERENCE

    logger.info(
        "mutation_gate.approved",
        trait=candidate.trait_name,
        delta=candidate.suggested_delta,
        evidence_count=len(candidate.evidence),
        day_span=observation_day_span,
    )
    return MutationDecision.APPROVED


def apply_confirmed_mutation(
    genome: Genome,
    candidate: MutationCandidate,
    practitioner_id: str,
    observation_day_span: int,
    context_count: int,
    has_cold_context_signal: bool,
) -> tuple[Genome, MutationLogEntry]:
    """
    Applies a human-confirmed, gate-approved mutation to a genome.
    Returns updated Genome and the MutationLogEntry to persist.

    This function must ONLY be called after:
    1. validate_mutation_gate() returned APPROVED
    2. Practitioner confirmed in mutation_review_screen

    DO NOT call this directly from Zone 2 or any automated process.
    """
    # Double-check gate — defensive re-validation
    existing_log: list[MutationLogEntry] = []  # Re-checked upstream, but we guard again
    gate_result = validate_mutation_gate(
        candidate=candidate,
        existing_log=existing_log,
        has_cold_context_signal=has_cold_context_signal,
        observation_day_span=observation_day_span,
        context_count=context_count,
    )
    if gate_result != MutationDecision.APPROVED:
        raise ValueError(
            f"apply_confirmed_mutation called but gate returned {gate_result}. "
            "This indicates a bug in the calling code."
        )

    # Compute new score — clamped to 1–100
    old_score = getattr(genome, candidate.trait_name)
    new_score = max(1, min(100, old_score + candidate.suggested_delta))

    # Apply to genome copy
    updated_data = genome.model_dump()
    updated_data[candidate.trait_name] = new_score

    updated_genome = Genome(**updated_data)

    # Build log entry
    log_entry = MutationLogEntry(
        prospect_id=candidate.prospect_id,
        trait_name=candidate.trait_name,
        old_score=old_score,
        new_score=new_score,
        delta=new_score - old_score,
        confirmed_by=practitioner_id,
        evidence_summary="; ".join(candidate.evidence[:5]),  # Max 5 evidence items
        gate_observations_count=len(candidate.evidence),
        gate_contexts_count=context_count,
        gate_day_span=observation_day_span,
    )

    logger.info(
        "genome_writer.mutation_applied",
        prospect_id=candidate.prospect_id,
        trait=candidate.trait_name,
        old=old_score,
        new=new_score,
        delta=new_score - old_score,
    )

    return updated_genome, log_entry
