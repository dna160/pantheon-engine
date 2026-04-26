"""
Module: session_analyzer.py
Zone: 3 (Post-session — harness + cloud LLM)
Input: session_id, JSONL log path, Genome, prospect_id, practitioner_id, LLMClient, config
Output: SessionAnalysisResult (mutation_candidates, practitioner_deltas, mirror_report)
LLM calls: 1 (zone3_session_analyzer prompt)
Side effects: None (harness_runner writes result to disk)
Latency tolerance: Async, up to 5 minutes

Zone 3 session analysis orchestrator.
Reads the JSONL session log produced by session_logger.py, structures it
for the LLM, calls the zone3_session_analyzer prompt, and parses the output
into typed Python objects.

The harness_runner calls analyze() after the practitioner ends the session.
The result is returned to mutation_review_screen (mobile) for human confirmation.
Genome writes NEVER happen automatically — always through genome_writer.py
after human confirmation.
"""

from __future__ import annotations

import json
import re
import uuid as _uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import structlog

from backend.genome.parameter_definitions import (
    Genome,
    MutationCandidate,
    MutationStrength,
)

logger = structlog.get_logger(__name__)

def _enrich_candidate_for_mobile(candidate: "MutationCandidate") -> dict:
    """
    Adds mobile-UI fields to a MutationCandidate dict.
    These fields don't exist in the core Pydantic model — they are UI helpers
    derived at serialization time so MutationReviewScreen can render cards.
    """
    base = {
        "prospect_id": candidate.prospect_id,
        "trait_name": candidate.trait_name,
        "current_score": candidate.current_score,
        "suggested_delta": candidate.suggested_delta,
        "suggested_new_score": candidate.suggested_new_score,
        "evidence": candidate.evidence,
        "strength": candidate.strength.value,
        "is_coherence_tension": candidate.is_coherence_tension,
    }

    # Derive direction from suggested_delta
    delta = candidate.suggested_delta
    if delta > 0:
        direction = "increase"
    elif delta < 0:
        direction = "decrease"
    else:
        direction = "recalibrate"

    # Rationale from first evidence item
    evidence = candidate.evidence or []
    rationale = evidence[0] if evidence else "Behavioral pattern observed across session."

    base["candidate_id"] = str(_uuid.uuid4())
    base["direction"] = direction
    base["rationale"] = rationale
    base["observation_count"] = len(evidence)

    return base


_FALLBACK_RESULT: dict = {
    "mutation_candidates": [],
    "practitioner_deltas": [],
    "mirror_report": {
        "signature_strength": "Analysis unavailable.",
        "blind_spot": "Analysis unavailable.",
        "instinct_ratio": "Analysis unavailable.",
        "pressure_signature": "Analysis unavailable.",
    },
    "outcome_log": {
        "outcome": "incomplete",
        "genome_state_at_close": {},
        "key_moments": [],
    },
}


@dataclass
class MirrorReport:
    """
    4-observation post-session report for the practitioner.
    NEVER shown on live HUD — post-session only (PRD CLAUDE.md Critical Constraint #6).
    """
    signature_strength: str     # Moment type where Hook/Close delta was consistently highest
    blind_spot: str             # Avoidance pattern with highest close cost
    instinct_ratio: str         # Override_success_rate with directional guidance
    pressure_signature: str     # Behavior under Irate/Identity Threat moments


@dataclass
class PractitionerDelta:
    """Single practitioner profile parameter update from this session."""
    parameter: str
    old_value: float
    new_value: float
    evidence: str


@dataclass
class SessionAnalysisResult:
    """
    Full output of Zone 3 analysis. Returned to mobile app for mutation review.
    mutation_candidates: list of MutationCandidate — each requires human confirmation
    practitioner_deltas: list of PractitionerDelta — applied to practitioner profile
    mirror_report: MirrorReport — shown post-session only
    outcome_log: dict — session outcome + key moments for Supabase
    raw_llm_output: str — preserved for debugging
    """
    mutation_candidates: list[MutationCandidate] = field(default_factory=list)
    practitioner_deltas: list[PractitionerDelta] = field(default_factory=list)
    mirror_report: Optional[MirrorReport] = None
    outcome_log: dict = field(default_factory=dict)
    session_id: str = ""
    analyzed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    raw_llm_output: str = ""
    is_fallback: bool = False

    def to_dict(self) -> dict:
        """Serializes to dict for mobile app JSON response."""
        return {
            "session_id": self.session_id,
            "analyzed_at": self.analyzed_at.isoformat(),
            "mutation_candidates": [
                _enrich_candidate_for_mobile(c)
                for c in self.mutation_candidates
            ],
            "practitioner_deltas": [
                {
                    "parameter": d.parameter,
                    "old_value": d.old_value,
                    "new_value": d.new_value,
                    "evidence": d.evidence,
                }
                for d in self.practitioner_deltas
            ],
            "mirror_report": {
                "signature_strength": self.mirror_report.signature_strength,
                "blind_spot": self.mirror_report.blind_spot,
                "instinct_ratio": self.mirror_report.instinct_ratio,
                "pressure_signature": self.mirror_report.pressure_signature,
            } if self.mirror_report else {},
            "outcome_log": self.outcome_log,
            "is_fallback": self.is_fallback,
        }


class SessionAnalyzer:
    """
    Zone 3 session analysis orchestrator.

    Usage (called by harness_runner after session ends):
        analyzer = SessionAnalyzer(
            log_path="./session_logs/{session_id}_{date}.jsonl",
            genome=genome,
            prospect_id="prospect-001",
            practitioner_id="practitioner-001",
        )
        result = await analyzer.analyze(llm_client, config)

    Zone 3 only. Called by harness_runner. Not used during Zone 2.
    """

    PROMPT_PATH = "skills/harness-orchestrator/prompts/zone3_session_analyzer.txt"

    def __init__(
        self,
        log_path: str,
        genome: Optional[Genome],
        prospect_id: str,
        practitioner_id: str,
        session_id: str,
    ) -> None:
        self._log_path = Path(log_path)
        self._genome = genome
        self._prospect_id = prospect_id
        self._practitioner_id = practitioner_id
        self._session_id = session_id

    async def analyze(self, llm_client, config) -> SessionAnalysisResult:
        """
        Main entry point. Reads log, calls LLM, parses response.
        Never raises — returns fallback result on any error.
        """
        try:
            events = self._load_log()
            prompt_input = self._build_prompt_input(events)

            system = self._load_prompt()
            raw = await llm_client.complete(
                prompt=json.dumps(prompt_input, default=str),
                system=system,
                config=config,
            )

            result = self._parse_result(raw)
            result.session_id = self._session_id
            result.raw_llm_output = raw

            logger.info(
                "session_analyzer.complete",
                session_id=self._session_id,
                mutation_candidates=len(result.mutation_candidates),
                practitioner_deltas=len(result.practitioner_deltas),
            )
            return result

        except Exception as e:
            logger.error("session_analyzer.error", error=str(e), session_id=self._session_id)
            return self._fallback_result()

    # ================================================================== #
    #  Log loading                                                          #
    # ================================================================== #

    def _load_log(self) -> list[dict]:
        """
        Read JSONL session log. Returns list of event dicts.
        Returns empty list if file not found.
        """
        if not self._log_path.exists():
            logger.warning("session_analyzer.log_not_found", path=str(self._log_path))
            return []

        events = []
        with open(self._log_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    logger.warning("session_analyzer.bad_log_line", line=line[:100])

        logger.info("session_analyzer.log_loaded", events=len(events), path=str(self._log_path))
        return events

    def _build_prompt_input(self, events: list[dict]) -> dict:
        """
        Structures raw event list into the input schema the
        zone3_session_analyzer.txt prompt expects.
        """
        moment_events = [e for e in events if e.get("event_type") == "moment_event"]
        snapshots = [e for e in events if e.get("event_type") == "periodic_snapshot"]
        option_choices = [e for e in events if e.get("event_type") == "option_choice"]
        divergence_alerts = [e for e in events if e.get("event_type") == "divergence_alert"]

        return {
            "session_id": self._session_id,
            "prospect_id": self._prospect_id,
            "practitioner_id": self._practitioner_id,
            "genome": self._genome.model_dump() if self._genome else {},
            "events": moment_events,
            "option_choices": option_choices,
            "divergence_alerts": divergence_alerts,
            "paralinguistic_snapshots": snapshots,
            "total_events": len(events),
            "session_duration_seconds": self._estimate_duration(events),
        }

    def _estimate_duration(self, events: list[dict]) -> float:
        """Estimate session duration from snapshot elapsed_seconds fields."""
        snapshots = [e for e in events if e.get("event_type") == "periodic_snapshot"]
        if not snapshots:
            return 0.0
        last = snapshots[-1]
        return float(last.get("elapsed_seconds", 0.0))

    # ================================================================== #
    #  Result parsing                                                       #
    # ================================================================== #

    def _parse_result(self, raw: str) -> SessionAnalysisResult:
        """
        Parse LLM JSON response into SessionAnalysisResult.
        Returns fallback if JSON parse fails or required fields missing.
        """
        clean = re.sub(r"```(?:json)?\s*|\s*```", "", raw).strip()
        data = json.loads(clean)

        mutation_candidates = self._parse_candidates(
            data.get("mutation_candidates", [])
        )
        practitioner_deltas = self._parse_practitioner_deltas(
            data.get("practitioner_deltas", [])
        )
        mirror_report = self._parse_mirror_report(
            data.get("mirror_report", {})
        )
        outcome_log = data.get("outcome_log", {})

        return SessionAnalysisResult(
            mutation_candidates=mutation_candidates,
            practitioner_deltas=practitioner_deltas,
            mirror_report=mirror_report,
            outcome_log=outcome_log,
            is_fallback=False,
        )

    def _parse_candidates(self, raw_list: list) -> list[MutationCandidate]:
        """Parse mutation candidates. Skips malformed entries."""
        candidates = []
        for item in raw_list:
            if not isinstance(item, dict):
                continue
            try:
                strength_raw = item.get("strength", "WEAK")
                try:
                    strength = MutationStrength(strength_raw)
                except ValueError:
                    strength = MutationStrength.WEAK

                candidate = MutationCandidate(
                    prospect_id=item.get("prospect_id", self._prospect_id),
                    trait_name=item.get("trait_name", ""),
                    current_score=int(item.get("current_score", 50)),
                    suggested_delta=int(item.get("suggested_delta", 0)),
                    suggested_new_score=int(item.get("suggested_new_score", 50)),
                    evidence=item.get("evidence", []),
                    strength=strength,
                    is_coherence_tension=bool(item.get("is_coherence_tension", False)),
                )
                # Skip empty/invalid candidates
                if candidate.trait_name:
                    candidates.append(candidate)
            except Exception as e:
                logger.warning(
                    "session_analyzer.candidate_parse_error",
                    error=str(e),
                    item=str(item)[:100],
                )

        return candidates

    def _parse_practitioner_deltas(self, raw_list: list) -> list[PractitionerDelta]:
        """Parse practitioner profile deltas. Skips malformed entries."""
        deltas = []
        for item in raw_list:
            if not isinstance(item, dict):
                continue
            try:
                deltas.append(PractitionerDelta(
                    parameter=item.get("parameter", ""),
                    old_value=float(item.get("old_value", 0)),
                    new_value=float(item.get("new_value", 0)),
                    evidence=item.get("evidence", ""),
                ))
            except Exception:
                pass
        return deltas

    def _parse_mirror_report(self, raw: dict) -> Optional[MirrorReport]:
        """Parse mirror report. Returns None if required fields missing."""
        if not isinstance(raw, dict):
            return None
        required = ("signature_strength", "blind_spot", "instinct_ratio", "pressure_signature")
        if not all(k in raw for k in required):
            return None
        return MirrorReport(
            signature_strength=raw.get("signature_strength", ""),
            blind_spot=raw.get("blind_spot", ""),
            instinct_ratio=raw.get("instinct_ratio", ""),
            pressure_signature=raw.get("pressure_signature", ""),
        )

    def _load_prompt(self) -> str:
        """Load zone3 analyzer prompt file. Returns stub if not found."""
        try:
            root = Path(__file__).resolve().parents[2]
            full_path = root / self.PROMPT_PATH
            if full_path.exists():
                return full_path.read_text()
        except Exception:
            pass
        return f"[PROMPT NOT FOUND: {self.PROMPT_PATH}]"

    def _fallback_result(self) -> SessionAnalysisResult:
        return SessionAnalysisResult(
            session_id=self._session_id,
            is_fallback=True,
            mirror_report=MirrorReport(
                signature_strength="Analysis unavailable.",
                blind_spot="Analysis unavailable.",
                instinct_ratio="Analysis unavailable.",
                pressure_signature="Analysis unavailable.",
            ),
        )
