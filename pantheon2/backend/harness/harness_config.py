"""
Module: harness_config.py
Zone: Foundation (loaded at startup, used by Zone 1 and 3)
Input: harness.config.json path
Output: HarnessConfig Pydantic model
LLM calls: 0
Side effects: Reads harness.config.json from disk once (lru_cache)
Latency tolerance: N/A (startup only)
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import BaseModel


class Zone1Config(BaseModel):
    provider: str = "anthropic"
    model: str = "claude-sonnet-4-6"
    max_tokens: int = 2000
    temperature: float = 0.3
    skill_ref: str = "skills/harness-orchestrator/prompts/zone1_cache_builder.txt"


class Zone2Config(BaseModel):
    slm_model_path: str = "./models/phi-3-mini-4k-instruct-q4_k_m.gguf"
    slm_backend: str = "llama_cpp"
    slm_max_tokens: int = 150
    slm_timeout_ms: int = 350
    fallback_to_cache: bool = True
    cache_path: str = "./session_cache/dialog_cache.json"


class Zone3Config(BaseModel):
    provider: str = "anthropic"
    model: str = "claude-sonnet-4-6"
    max_tokens: int = 3000
    temperature: float = 0.4
    skill_ref: str = "skills/harness-orchestrator/prompts/zone3_session_analyzer.txt"


class PsychReviewConfig(BaseModel):
    provider: str = "anthropic"
    model: str = "claude-sonnet-4-6"
    max_tokens: int = 1500
    temperature: float = 0.2
    validity_prompt_ref: str = "skills/adversarial-psychologist/prompts/validity_review.txt"
    ecological_prompt_ref: str = "skills/adversarial-psychologist/prompts/ecological_validity_review.txt"


class HarnessConfig(BaseModel):
    zone1: Zone1Config = Zone1Config()
    zone2: Zone2Config = Zone2Config()
    zone3: Zone3Config = Zone3Config()
    psych_review: PsychReviewConfig = PsychReviewConfig()


@lru_cache(maxsize=1)
def load_harness_config(config_path: Optional[str] = None) -> HarnessConfig:
    """
    Loads harness.config.json from disk. Cached after first load.
    To swap LLMs: edit harness.config.json only — no code changes needed.
    """
    if config_path is None:
        # Resolve relative to pantheon2/ root (parents[2] from this file's location)
        root = Path(__file__).resolve().parents[2]
        config_path = str(root / "harness.config.json")

    path = Path(config_path)
    if not path.exists():
        # Return defaults if config file is missing
        return HarnessConfig()

    with open(path) as f:
        raw = json.load(f)

    # Strip _comment field if present
    raw.pop("_comment", None)
    raw.pop("supported_providers", None)

    return HarnessConfig(
        zone1=Zone1Config(**raw.get("zone1", {})),
        zone2=Zone2Config(**raw.get("zone2", {})),
        zone3=Zone3Config(**raw.get("zone3", {})),
        psych_review=PsychReviewConfig(**raw.get("psych_review", {})),
    )
