"""
Module: slm_config.py
Zone: 2 (Live session)
Input: Zone2Config from harness_config
Output: SLMConfig Pydantic model
LLM calls: 0
Side effects: None
Latency tolerance: N/A (startup only)
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import BaseModel


class SLMConfig(BaseModel):
    model_path: str = "./models/phi-3-mini-4k-instruct-q4_k_m.gguf"
    backend: str = "llama_cpp"          # "llama_cpp" | "onnx"
    max_tokens: int = 150
    timeout_ms: int = 350               # Hard limit per PRD — fallback to cache if exceeded
    temperature: float = 0.1            # Low temp for deterministic adaptation
    fallback_to_cache: bool = True

    @property
    def model_exists(self) -> bool:
        return Path(self.model_path).exists()

    @classmethod
    def from_zone2_config(cls, zone2_config) -> "SLMConfig":
        return cls(
            model_path=getattr(zone2_config, "slm_model_path", "./models/phi-3-mini-4k-instruct-q4_k_m.gguf"),
            max_tokens=getattr(zone2_config, "slm_max_tokens", 150),
            timeout_ms=getattr(zone2_config, "slm_timeout_ms", 350),
            fallback_to_cache=getattr(zone2_config, "fallback_to_cache", True),
        )
