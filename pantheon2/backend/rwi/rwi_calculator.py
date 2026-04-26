"""
Module: rwi_calculator.py
Zone: 1 (Pre-session)
Input: Genome, list[DeltaSignal] (optional)
Output: RWISnapshot
LLM calls: 0
Side effects: None
Latency tolerance: <500ms

RWI = Receptivity Window Index (0–100)
Measures when a prospect is most psychologically open to a commitment.
Computed from genome signals, not from live session data.
Updated in Observed State during session by bar_calculator.py.
"""

from __future__ import annotations

from backend.genome.parameter_definitions import (
    Genome,
    RWIComponents,
    RWISnapshot,
    DeltaSignal,
    DeltaSignalType,
    rwi_window_status,
)


class RWICalculator:
    """
    Computes the Receptivity Window Index from a genome and optional delta signals.

    Components:
      Validation Recency    → rises with recent public professional wins
      Friction Saturation   → rises with accumulated systemic pressure
      Decision Fatigue      → rises with role complexity / cognitive load proxies
      Identity Momentum     → rises when prospect is in expansion mode
    """

    def calculate(
        self,
        genome: Genome,
        delta_signals: list[DeltaSignal] | None = None,
    ) -> RWISnapshot:
        """
        Returns a full RWISnapshot.
        Delta signals adjust RWI components before the final score is computed.
        """
        components = self._compute_components(genome)
        components = self._apply_delta_signals(components, delta_signals or [])
        score = self._compute_score(components)
        window_status, strategy_note = rwi_window_status(score)

        return RWISnapshot(
            prospect_id=genome.prospect_id,
            score=score,
            components=components,
            window_status=window_status,
            strategy_note=strategy_note,
        )

    # ------------------------------------------------------------------ #
    #  Component derivations from genome                                   #
    # ------------------------------------------------------------------ #

    def _compute_components(self, g: Genome) -> RWIComponents:
        return RWIComponents(
            validation_recency=self._validation_recency(g),
            friction_saturation=self._friction_saturation(g),
            decision_fatigue_estimate=self._decision_fatigue(g),
            identity_momentum=self._identity_momentum(g),
        )

    def _validation_recency(self, g: Genome) -> int:
        """
        Derived from public_validation_events proxy in genome.
        We use influence_susceptibility and identity_fusion as secondary signals —
        people who care about public validation will show stronger recency effects.
        High: recent promotion/award → RWI rises.
        In absence of explicit validation data, default to neutral (50).
        """
        base = 50
        # High identity_fusion + high influence_susceptibility = more responsive to validation
        modifier = int((g.identity_fusion - 50) * 0.2 + (g.influence_susceptibility - 50) * 0.1)
        return _clamp(base + modifier)

    def _friction_saturation(self, g: Genome) -> int:
        """
        High friction saturation → RWI drops.
        Derived directly from socioeconomic_friction and neuroticism.
        """
        raw = int((g.socioeconomic_friction * 0.6) + (g.neuroticism * 0.4))
        return _clamp(raw)

    def _decision_fatigue(self, g: Genome) -> int:
        """
        Proxy: high conscientiousness + high communication complexity = more decisions to manage.
        High fatigue → RWI drops.
        """
        raw = int((g.conscientiousness * 0.4) + (g.literacy_and_articulation * 0.2) + 20)
        # Executive_flexibility HIGH means they manage fatigue better → reduce fatigue score
        fatigue_offset = int((g.executive_flexibility - 50) * 0.2)
        return _clamp(raw - fatigue_offset)

    def _identity_momentum(self, g: Genome) -> int:
        """
        Identity momentum: is the prospect in expansion or consolidation mode?
        Proxy: high chronesthesia_capacity + high openness = more likely in expansion.
        High: expansion → RWI rises.
        """
        raw = int((g.chronesthesia_capacity * 0.5) + (g.openness * 0.3) + 10)
        return _clamp(raw)

    # ------------------------------------------------------------------ #
    #  Delta signal adjustments                                            #
    # ------------------------------------------------------------------ #

    def _apply_delta_signals(
        self,
        components: RWIComponents,
        signals: list[DeltaSignal],
    ) -> RWIComponents:
        """Adjust RWI components based on fresh social signals from Signal Delta pipeline."""
        for signal in signals:
            if signal.signal_type == DeltaSignalType.VALIDATION_EVENT:
                components.validation_recency = _clamp(
                    components.validation_recency + abs(signal.rwi_impact)
                )
            elif signal.signal_type == DeltaSignalType.FRICTION_SIGNAL:
                components.friction_saturation = _clamp(
                    components.friction_saturation + abs(signal.rwi_impact)
                )
            elif signal.signal_type == DeltaSignalType.IDENTITY_MOMENTUM:
                components.identity_momentum = _clamp(
                    components.identity_momentum + abs(signal.rwi_impact)
                )
            elif signal.signal_type == DeltaSignalType.CONSOLIDATION:
                components.identity_momentum = _clamp(
                    components.identity_momentum - abs(signal.rwi_impact)
                )
        return components

    # ------------------------------------------------------------------ #
    #  Final score computation                                             #
    # ------------------------------------------------------------------ #

    def _compute_score(self, c: RWIComponents) -> int:
        """
        Weighted formula:
          + Validation Recency:   rises RWI
          - Friction Saturation:  drops RWI  (inverted)
          - Decision Fatigue:     drops RWI  (inverted)
          + Identity Momentum:    rises RWI

        Weights chosen to give friction saturation the highest drag
        (real systemic pressure is the strongest window-closer).
        """
        score = (
            c.validation_recency * 0.25
            + (100 - c.friction_saturation) * 0.35   # inverted
            + (100 - c.decision_fatigue_estimate) * 0.15  # inverted
            + c.identity_momentum * 0.25
        )
        return _clamp(int(score))


def _clamp(val: int) -> int:
    return max(0, min(100, val))
