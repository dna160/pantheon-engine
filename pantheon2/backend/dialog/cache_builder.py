"""
Module: cache_builder.py
Zone: 1 (Pre-session — main LLM call)
Input: GenomeBundle, RWISnapshot, LLMClient, Zone1Config
Output: validated + probability-adjusted dialog cache dict (6×3 options)
LLM calls: 1 (zone1_cache_builder prompt)
Side effects: None (harness_runner writes result to disk)
Latency tolerance: 30–120s (main Zone 1 LLM call)

Builds the 18-option dialog cache from genome + RWI via the harness LLM.
Validates structure, fills in missing moment types with fallback options,
then runs probability_engine adjustments.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import structlog

from backend.genome.parameter_definitions import GenomeBundle, RWISnapshot
from backend.dialog.probability_engine import ProbabilityEngine

logger = structlog.get_logger(__name__)

MOMENT_TYPES = [
    "neutral_exploratory",
    "irate_resistant",
    "topic_avoidance",
    "identity_threat",
    "high_openness",
    "closing_signal",
]

_FALLBACK_OPTION = {
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


class CacheBuilder:
    """
    Orchestrates the Zone 1 LLM call to build the dialog cache,
    validates the response structure, and applies probability adjustments.
    """

    def __init__(self, llm_client, config) -> None:
        self._llm = llm_client
        self._config = config
        self._prob_engine = ProbabilityEngine()

    async def build(self, genome_bundle: GenomeBundle, rwi: RWISnapshot) -> dict:
        """
        Main entry point. Returns fully validated + adjusted cache dict.
        Never raises — returns fallback cache on any error.
        """
        try:
            raw = await self._call_llm(genome_bundle, rwi)
            parsed = self._parse_response(raw)
            validated = self._validate_and_fill(parsed)
            adjusted = self._prob_engine.adjust(
                validated,
                genome_bundle.genome,
                genome_bundle.confidence,
                rwi,
            )
            logger.info(
                "cache_builder.built",
                moment_types=len([k for k in adjusted if k in MOMENT_TYPES]),
                is_fallback=False,
            )
            return adjusted
        except Exception as e:
            logger.error("cache_builder.error", error=str(e))
            return self._full_fallback_cache()

    async def _call_llm(self, genome_bundle: GenomeBundle, rwi: RWISnapshot) -> str:
        system = self._load_prompt(
            "skills/harness-orchestrator/prompts/zone1_cache_builder.txt"
        )
        prompt = json.dumps(
            {
                "genome": genome_bundle.genome.model_dump(),
                "confidence": genome_bundle.confidence.value,
                "rwi": rwi.model_dump(),
                "market_context": "Indonesia B2B Advisory",
            },
            default=self._json_default,
        )
        return await self._llm.complete(
            prompt=prompt,
            system=system,
            config=self._config,
        )

    @staticmethod
    def _json_default(obj):
        from datetime import datetime
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    def _parse_response(self, raw: str) -> dict:
        clean = re.sub(r"```(?:json)?\s*|\s*```", "", raw).strip()
        return json.loads(clean)

    def _validate_and_fill(self, parsed: dict) -> dict:
        """
        Ensures all 6 moment types are present and each has option_a/b/c.
        Fills missing entries with fallback options.
        """
        result = {}
        for moment in MOMENT_TYPES:
            moment_data = parsed.get(moment, {})
            if not isinstance(moment_data, dict):
                moment_data = {}
            options = {}
            for opt_key in ("option_a", "option_b", "option_c"):
                opt = moment_data.get(opt_key)
                if isinstance(opt, dict) and "base_language" in opt:
                    if "base_probability" not in opt:
                        opt["base_probability"] = 50
                    options[opt_key] = opt
                else:
                    options[opt_key] = dict(_FALLBACK_OPTION[opt_key])
            result[moment] = options
        result["_is_fallback"] = False
        return result

    def _full_fallback_cache(self) -> dict:
        import copy
        result = {moment: copy.deepcopy(_FALLBACK_OPTION) for moment in MOMENT_TYPES}
        result["_is_fallback"] = True
        return result

    def _load_prompt(self, relative_path: str) -> str:
        try:
            root = Path(__file__).resolve().parents[2]
            full_path = root / relative_path
            if full_path.exists():
                return full_path.read_text()
        except Exception:
            pass
        return f"[PROMPT NOT FOUND: {relative_path}]"
