"""
Module: probability_engine.py
Zone: 1 (Post-cache-build — adjusts LLM-assigned base probabilities)
Input: raw dialog cache dict, Genome, ConfidenceLevel, RWISnapshot
Output: adjusted cache dict (same structure, probabilities modified)
LLM calls: 0
Side effects: None
Latency tolerance: <50ms

Applies rule-based probability compression and genome-derived adjustments to
the LLM-built dialog cache. Ensures options sum to ~150 per moment type (3×50),
and that genome traits modulate which option is statistically preferred.
"""

from __future__ import annotations

from backend.genome.parameter_definitions import Genome, ConfidenceLevel, RWISnapshot


_MOMENT_TYPES = [
    "neutral_exploratory",
    "irate_resistant",
    "topic_avoidance",
    "identity_threat",
    "high_openness",
    "closing_signal",
]

_OPTION_KEYS = ["option_a", "option_b", "option_c"]


class ProbabilityEngine:
    """
    Adjusts dialog cache probabilities based on genome traits, confidence level,
    and RWI score. All adjustments are additive deltas clamped to [10, 90].
    """

    def adjust(
        self,
        cache: dict,
        genome: Genome,
        confidence: ConfidenceLevel,
        rwi: RWISnapshot,
    ) -> dict:
        """
        Returns a new cache dict with adjusted base_probability values.
        Preserves all other cache fields.
        """
        import copy
        adjusted = copy.deepcopy(cache)

        for moment_type in _MOMENT_TYPES:
            if moment_type not in adjusted or not isinstance(adjusted[moment_type], dict):
                continue
            options = adjusted[moment_type]
            self._apply_confidence_compression(options, confidence)
            self._apply_genome_adjustments(options, moment_type, genome)
            self._apply_rwi_adjustments(options, moment_type, rwi)

        return adjusted

    # ------------------------------------------------------------------ #
    #  Confidence compression — mirrors confidence_scorer logic           #
    # ------------------------------------------------------------------ #

    def _apply_confidence_compression(
        self, options: dict, confidence: ConfidenceLevel
    ) -> None:
        """
        LOW confidence → compress all probabilities 15pts toward 50.
        MEDIUM confidence → compress 7pts toward 50.
        HIGH confidence → no compression.
        """
        if confidence == ConfidenceLevel.HIGH:
            return

        compression = 15 if confidence == ConfidenceLevel.LOW else 7

        for key in _OPTION_KEYS:
            option = options.get(key)
            if not isinstance(option, dict):
                continue
            prob = option.get("base_probability", 50)
            delta = prob - 50
            if abs(delta) <= compression:
                option["base_probability"] = 50
            else:
                option["base_probability"] = prob - (compression if delta > 0 else -compression)

    # ------------------------------------------------------------------ #
    #  Genome adjustments per moment type                                  #
    # ------------------------------------------------------------------ #

    def _apply_genome_adjustments(
        self, options: dict, moment_type: str, genome: Genome
    ) -> None:
        """
        Boosts/reduces option probabilities based on genome trait alignment.
        All adjustments are applied as additive deltas, then clamped [10, 90].
        """
        if moment_type == "irate_resistant":
            self._adjust_irate_options(options, genome)
        elif moment_type == "identity_threat":
            self._adjust_identity_threat_options(options, genome)
        elif moment_type == "high_openness":
            self._adjust_high_openness_options(options, genome)
        elif moment_type == "closing_signal":
            self._adjust_closing_options(options, genome)

        self._clamp_all(options)

    def _adjust_irate_options(self, options: dict, genome: Genome) -> None:
        """High agreeableness → prefer softer de-escalation (option_a typically)."""
        if genome.agreeableness is not None and genome.agreeableness > 65:
            self._delta(options, "option_a", +8)
            self._delta(options, "option_c", -4)
        if genome.neuroticism is not None and genome.neuroticism > 65:
            self._delta(options, "option_a", +5)  # slower/softer with high-anxiety prospects

    def _adjust_identity_threat_options(self, options: dict, genome: Genome) -> None:
        """High identity_fusion → identity threat is acute; prefer validation approach."""
        if genome.identity_fusion is not None and genome.identity_fusion > 65:
            self._delta(options, "option_a", +10)
            self._delta(options, "option_b", -5)
        if genome.tom_self_awareness is not None and genome.tom_self_awareness > 65:
            self._delta(options, "option_b", +6)  # meta-awareness → can engage reflectively

    def _adjust_high_openness_options(self, options: dict, genome: Genome) -> None:
        """High chronesthesia → vision hooks land well; boost forward-frame options."""
        if genome.chronesthesia_capacity is not None and genome.chronesthesia_capacity > 65:
            self._delta(options, "option_b", +8)
        if genome.openness is not None and genome.openness > 70:
            self._delta(options, "option_a", +5)

    def _adjust_closing_options(self, options: dict, genome: Genome) -> None:
        """High decision_making → prefers decisive close; boost direct options."""
        if genome.decision_making is not None and genome.decision_making > 65:
            self._delta(options, "option_c", +8)
        if genome.influence_susceptibility is not None and genome.influence_susceptibility > 65:
            self._delta(options, "option_b", +5)  # social proof options land better

    # ------------------------------------------------------------------ #
    #  RWI adjustments                                                     #
    # ------------------------------------------------------------------ #

    def _apply_rwi_adjustments(
        self, options: dict, moment_type: str, rwi: RWISnapshot
    ) -> None:
        """
        Peak RWI → boost closing_signal options broadly.
        Closed RWI → soften all options (reduce max spread).
        """
        if rwi.window_status == "peak" and moment_type == "closing_signal":
            for key in _OPTION_KEYS:
                self._delta(options, key, +5)
        elif rwi.window_status == "closed":
            for key in _OPTION_KEYS:
                option = options.get(key)
                if isinstance(option, dict):
                    prob = option.get("base_probability", 50)
                    delta = prob - 50
                    if abs(delta) > 10:
                        option["base_probability"] = 50 + (10 if delta > 0 else -10)

        self._clamp_all(options)

    # ------------------------------------------------------------------ #
    #  Helpers                                                             #
    # ------------------------------------------------------------------ #

    def _delta(self, options: dict, key: str, delta: int) -> None:
        option = options.get(key)
        if isinstance(option, dict) and "base_probability" in option:
            option["base_probability"] = option["base_probability"] + delta

    def _clamp_all(self, options: dict) -> None:
        for key in _OPTION_KEYS:
            option = options.get(key)
            if isinstance(option, dict) and "base_probability" in option:
                option["base_probability"] = max(10, min(90, option["base_probability"]))
