"""
Module: confidence_scorer.py
Zone: 1 (Pre-session)
Input: resolver_path str, mutation_log_count int, genome_age_days int | None
Output: ConfidenceLevel, probability_spread int
LLM calls: 0
Side effects: None
Latency tolerance: <10ms
"""

from __future__ import annotations

from backend.genome.parameter_definitions import ConfidenceLevel

# Probability spread per confidence level (±points on dialog option probability bars)
CONFIDENCE_SPREADS: dict[ConfidenceLevel, int] = {
    ConfidenceLevel.HIGH: 12,
    ConfidenceLevel.MEDIUM: 18,
    ConfidenceLevel.LOW: 25,
}

# Genome is considered stale after this many days without a mutation log entry
GENOME_STALE_DAYS = 90


def score_confidence(
    resolver_path: str,
    mutation_log_count: int,
    genome_age_days: int | None,
) -> ConfidenceLevel:
    """
    Derives confidence level from how the genome was obtained and how fresh it is.

    HIGH  → Loaded from Supabase, age < 90 days, at least 1 confirmed mutation
    MEDIUM → Fresh scrape (LinkedIn + Instagram)
    LOW   → Manual intake form only
    """
    if resolver_path == "supabase":
        age_ok = genome_age_days is not None and genome_age_days < GENOME_STALE_DAYS
        has_mutations = mutation_log_count >= 1
        if age_ok and has_mutations:
            return ConfidenceLevel.HIGH
        # Supabase genome but stale or no mutations → treat as MEDIUM
        return ConfidenceLevel.MEDIUM

    if resolver_path == "fresh_scrape":
        return ConfidenceLevel.MEDIUM

    # intake_form or unknown
    return ConfidenceLevel.LOW


def probability_spread(confidence: ConfidenceLevel) -> int:
    """Returns the ± probability spread for HUD rendering."""
    return CONFIDENCE_SPREADS[confidence]


def apply_low_confidence_penalty(scores: dict[str, int]) -> dict[str, int]:
    """
    When confidence is LOW, compress all genome scores toward 50 by 15 points.
    Per PRD: 'Manual intake form → all probability weights compressed by 15 points.'
    """
    compressed = {}
    for trait, val in scores.items():
        if val > 50:
            compressed[trait] = max(50, val - 15)
        elif val < 50:
            compressed[trait] = min(50, val + 15)
        else:
            compressed[trait] = val
    return compressed
