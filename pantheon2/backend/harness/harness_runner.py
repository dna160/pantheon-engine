"""
Module: harness_runner.py
Zone: 1 and 3 (orchestrates both; never touches Zone 2)
Input: prospect_id, practitioner_id
Output: SessionBundle ready for Zone 2
LLM calls: Zone 1 = 2 (cache build + psych review), Zone 3 = 1 (session analysis)
Side effects: Supabase reads/writes, local cache file write
Latency tolerance: 2–5 minutes (Zone 1), async (Zone 3)

This is the main entry point for both pre-session setup and post-session teardown.
Zone 2 (live session) is completely separate — harness_runner has no role there.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import structlog

from backend.harness.harness_config import load_harness_config, HarnessConfig
from backend.harness.llm_client import LLMClient
from backend.genome.genome_resolver import GenomeResolver
from backend.genome.parameter_definitions import GenomeBundle, RWISnapshot
from backend.rwi.rwi_calculator import RWICalculator
from backend.signal_delta.delta_pipeline import run_signal_delta_pipeline
from backend.db.genome_repo import GenomeRepo

logger = structlog.get_logger(__name__)


class SessionBundle:
    """Everything Zone 2 needs to start. Passed to session_runner.py."""

    def __init__(
        self,
        session_id: str,
        prospect_id: str,
        practitioner_id: str,
        genome_bundle: GenomeBundle,
        rwi: RWISnapshot,
        dialog_cache: dict,
        psych_report: dict,
        cache_path: str,
    ):
        self.session_id = session_id
        self.prospect_id = prospect_id
        self.practitioner_id = practitioner_id
        self.genome_bundle = genome_bundle
        self.rwi = rwi
        self.dialog_cache = dialog_cache
        self.psych_report = psych_report
        self.cache_path = cache_path


class HarnessRunner:
    """
    Orchestrates Zone 1 (pre-session) and Zone 3 (post-session).
    Zone 2 runs independently — this class is dormant during live session.
    """

    def __init__(self, config: HarnessConfig | None = None) -> None:
        self.config = config or load_harness_config()
        self.llm = LLMClient()
        self.genome_resolver = GenomeResolver()
        self.rwi_calculator = RWICalculator()
        self.genome_repo = GenomeRepo()

    # ================================================================== #
    #  ZONE 1: PRE-SESSION SETUP                                          #
    # ================================================================== #

    async def prepare_session(
        self,
        session_id: str,
        prospect_id: str,
        practitioner_id: str,
    ) -> SessionBundle:
        """
        Full Zone 1 pipeline. Returns SessionBundle for Zone 2.

        Steps (some run concurrently):
          1. Genome resolution (Supabase → scrape → intake)
          2. Signal delta pipeline (parallel with genome resolution)
          3. RWI calculation
          4. Psych review (adversarial agent)
          5. Dialog cache build (main LLM call)
          6. SLM warm-up (parallel with LLM call)
        """
        logger.info("harness.zone1.starting", session_id=session_id, prospect_id=prospect_id)

        # --- Step 1 + 2: Genome resolution and signal delta in parallel ---
        last_scrape_ts = self.genome_repo.get_last_scrape_timestamp(prospect_id)

        genome_bundle, (delta_signals, _) = await asyncio.gather(
            self.genome_resolver.resolve(prospect_id),
            run_signal_delta_pipeline(
                prospect_id=prospect_id,
                session_id=session_id,
                last_scrape_timestamp=last_scrape_ts,
                base_rwi=50,  # placeholder — will be recalculated with genome
            ),
        )

        # Attach delta signals to bundle
        genome_bundle.delta_signals = delta_signals

        # --- Step 3: RWI with delta signals ---
        rwi = self.rwi_calculator.calculate(
            genome=genome_bundle.genome,
            delta_signals=delta_signals,
        )
        genome_bundle.rwi = rwi

        logger.info(
            "harness.zone1.genome_resolved",
            confidence=genome_bundle.confidence.value,
            rwi=rwi.score,
            window=rwi.window_status,
            delta_signals=len(delta_signals),
        )

        # --- Step 4 + 5: Psych review and cache build in parallel ---
        psych_report, cache_result = await asyncio.gather(
            self._run_psych_review(genome_bundle),
            self._build_dialog_cache(genome_bundle, rwi),
        )

        # --- Step 6: SLM warm-up (fire and forget — don't block on it) ---
        asyncio.create_task(self._warm_slm())

        # Write cache to disk for Zone 2 local lookup
        cache_path = self._write_cache(session_id, cache_result)

        logger.info("harness.zone1.complete", session_id=session_id, cache_path=cache_path)

        return SessionBundle(
            session_id=session_id,
            prospect_id=prospect_id,
            practitioner_id=practitioner_id,
            genome_bundle=genome_bundle,
            rwi=rwi,
            dialog_cache=cache_result,
            psych_report=psych_report,
            cache_path=cache_path,
        )

    async def _run_psych_review(self, genome_bundle: GenomeBundle) -> dict:
        """Runs the adversarial psychology review agent."""
        try:
            system = self._load_prompt("skills/adversarial-psychologist/prompts/validity_review.txt")
            prompt = json.dumps({
                "genome": genome_bundle.genome.model_dump(),
                "confidence": genome_bundle.confidence.value,
                "market_context": "Indonesia B2B Advisory",
            })
            raw = await self.llm.complete(
                prompt=prompt,
                system=system,
                config=self.config.psych_review,
            )
            return self._parse_json_response(raw, fallback={
                "genome_validity_score": "PARTIAL",
                "ecological_validity_score": "PARTIAL",
                "flags": [],
                "high_severity_count": 0,
                "requires_acknowledgment": False,
                "summary": "Psych review unavailable — proceed with standard caution.",
            })
        except Exception as e:
            logger.error("harness.psych_review.error", error=str(e))
            return {"flags": [], "high_severity_count": 0, "requires_acknowledgment": False,
                    "summary": "Psych review unavailable."}

    async def _build_dialog_cache(self, genome_bundle: GenomeBundle, rwi: RWISnapshot) -> dict:
        """
        Main Zone 1 LLM call. Builds the 18-option dialog cache
        (6 moment types × 3 options each), genome-calibrated.
        """
        try:
            system = self._load_prompt("skills/harness-orchestrator/prompts/zone1_cache_builder.txt")
            prompt = json.dumps({
                "genome": genome_bundle.genome.model_dump(),
                "confidence": genome_bundle.confidence.value,
                "rwi": rwi.model_dump(),
                "market_context": "Indonesia B2B Advisory",
            })
            raw = await self.llm.complete(
                prompt=prompt,
                system=system,
                config=self.config.zone1,
            )
            cache = self._parse_json_response(raw, fallback=self._generic_fallback_cache())
            logger.info("harness.cache_built", option_count=self._count_options(cache))
            return cache
        except Exception as e:
            logger.error("harness.cache_build.error", error=str(e))
            return self._generic_fallback_cache()

    async def _warm_slm(self) -> None:
        """Pre-loads local SLM into memory so Zone 2 first inference is fast."""
        try:
            from backend.slm.slm_warmer import SLMWarmer
            warmer = SLMWarmer(self.config.zone2)
            await warmer.warm_up()
        except Exception as e:
            logger.warning("harness.slm_warm.failed", error=str(e))

    # ================================================================== #
    #  ZONE 3: POST-SESSION ANALYSIS                                       #
    # ================================================================== #

    async def analyze_session(
        self,
        session_id: str,
        prospect_id: str,
        practitioner_id: str,
    ) -> dict:
        """
        Zone 3: Analyzes session log and returns mutation candidates
        + practitioner deltas + mirror report.
        """
        from backend.db.session_repo import SessionRepo
        session_repo = SessionRepo()

        events = session_repo.get_session_events(session_id)
        para_snapshots = session_repo.get_paralinguistic_snapshots(session_id)
        genome = self.genome_repo.get_by_prospect_id(prospect_id)

        try:
            system = self._load_prompt(
                "skills/harness-orchestrator/prompts/zone3_session_analyzer.txt"
            )
            prompt = json.dumps({
                "session_id": session_id,
                "events": [e.model_dump() for e in events],
                "paralinguistic_snapshots": [p.model_dump() for p in para_snapshots],
                "genome": genome.model_dump() if genome else {},
                "prospect_id": prospect_id,
                "practitioner_id": practitioner_id,
            }, default=str)

            raw = await self.llm.complete(
                prompt=prompt,
                system=system,
                config=self.config.zone3,
            )
            result = self._parse_json_response(raw, fallback={
                "mutation_candidates": [],
                "practitioner_deltas": [],
                "mirror_report": {},
            })
            self._save_analysis(session_id, result)
            logger.info(
                "harness.zone3.complete",
                session_id=session_id,
                mutation_candidates=len(result.get("mutation_candidates", [])),
            )
            return result
        except Exception as e:
            logger.error("harness.zone3.error", error=str(e))
            return {"mutation_candidates": [], "practitioner_deltas": [], "mirror_report": {}}

    # ================================================================== #
    #  Helpers                                                             #
    # ================================================================== #

    def _write_cache(self, session_id: str, cache: dict) -> str:
        """Writes dialog cache to local filesystem for Zone 2 lookup."""
        cache_dir = Path("./session_cache")
        cache_dir.mkdir(exist_ok=True)
        cache_path = cache_dir / f"{session_id}_dialog_cache.json"
        with open(cache_path, "w") as f:
            json.dump(cache, f, indent=2)
        return str(cache_path)

    def _save_analysis(self, session_id: str, result: dict) -> None:
        """Persists Zone 3 analysis to disk for mobile app polling."""
        cache_dir = Path("./session_cache")
        cache_dir.mkdir(exist_ok=True)
        out_path = cache_dir / f"{session_id}_analysis.json"
        with open(out_path, "w") as f:
            json.dump(result, f, indent=2, default=str)

    def _load_prompt(self, relative_path: str) -> str:
        """Loads a prompt file relative to pantheon2/ project root."""
        try:
            # parents[2] from backend/harness/harness_runner.py → pantheon2/
            root = Path(__file__).resolve().parents[2]
            full_path = root / relative_path
            if full_path.exists():
                return full_path.read_text()
        except Exception:
            pass
        return f"[PROMPT FILE NOT FOUND: {relative_path}]"

    def _parse_json_response(self, raw: str, fallback: dict) -> dict:
        """Safely parses LLM JSON response. Returns fallback on parse failure."""
        import re
        try:
            clean = re.sub(r"```(?:json)?\s*|\s*```", "", raw).strip()
            return json.loads(clean)
        except Exception as e:
            logger.warning("harness.json_parse_failed", error=str(e), raw_preview=raw[:200])
            return fallback

    def _count_options(self, cache: dict) -> int:
        total = 0
        for moment_key, options in cache.items():
            if isinstance(options, dict):
                total += len(options)
        return total

    def _generic_fallback_cache(self) -> dict:
        """
        Bundled fallback cache when LLM call fails.
        Generic options with 50% probability (no genome calibration).
        Practitioner sees LOW confidence warning on HUD.
        """
        generic_options = {
            "option_a": {
                "core_approach": "Acknowledge and explore",
                "base_language": "It sounds like there's something important here. Can you tell me more about what's driving that?",
                "trigger_phrase": "Explore the why",
                "base_probability": 50,
                "genome_rationale": "Generic fallback — genome calibration unavailable.",
            },
            "option_b": {
                "core_approach": "Reframe toward value",
                "base_language": "Let me approach this differently — what would success look like for you in 12 months?",
                "trigger_phrase": "Reframe to value",
                "base_probability": 50,
                "genome_rationale": "Generic fallback.",
            },
            "option_c": {
                "core_approach": "Build rapport and slow down",
                "base_language": "I want to make sure I understand your situation fully before we go further. What matters most to you right now?",
                "trigger_phrase": "Slow and listen",
                "base_probability": 50,
                "genome_rationale": "Generic fallback.",
            },
        }
        return {
            "neutral_exploratory": generic_options,
            "irate_resistant": generic_options,
            "topic_avoidance": generic_options,
            "identity_threat": generic_options,
            "high_openness": generic_options,
            "closing_signal": generic_options,
            "_is_fallback": True,
        }
