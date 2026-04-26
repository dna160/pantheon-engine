"""
Module: local_classifier.py
Zone: 2 (Live session — no network, no cloud calls)
Input: transcript text (str), ObservedState
Output: (MomentType, confidence float)
LLM calls: 0
Side effects: None
Latency tolerance: <10ms (pure rule-based)

Rule-based 6-type moment classifier. Uses keyword patterns and signal rules
calibrated for Indonesian B2B context per PRD 3.3 and adversarial flags.

Indonesian B2B calibrations applied (per PRD 7.2 and adversarial-psychologist/SKILL.md):
- Irate/Resistant: indirect signals — over-politeness, "ya betul" flooding, question deflection
- Topic Avoidance: basa-basi not classified as avoidance in first 90s
- Closing Signal: indirect Indonesian signals ("boleh minta proposal?", "kapan bisa mulai?")
- Identity Threat: seniority/title references, third-party authority deflection
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Optional


class MomentType(str, Enum):
    NEUTRAL_EXPLORATORY = "neutral_exploratory"
    IRATE_RESISTANT = "irate_resistant"
    TOPIC_AVOIDANCE = "topic_avoidance"
    IDENTITY_THREAT = "identity_threat"
    HIGH_OPENNESS = "high_openness"
    CLOSING_SIGNAL = "closing_signal"


# ------------------------------------------------------------------ #
#  Keyword pattern sets — bilingual EN + Indonesian                   #
# ------------------------------------------------------------------ #

_IRATE_DIRECT = [
    r"tidak (mau|bisa|perlu|tertarik)",
    r"tidak relevan", r"tidak sesuai",
    r"sudah cukup", r"tidak usah",
    r"not interested", r"too expensive", r"don't need",
    r"stop", r"enough", r"ridiculous",
]

# Indonesian indirect resistance — per PRD adversarial findings
_IRATE_INDIRECT = [
    r"\bya betul\b.{0,30}\bya betul\b",   # repeated affirmation without engagement
    r"\btentu saja\b.{0,30}\btentu saja\b",
    r"nanti (saya|kami) pikir",
    r"nanti (saya|kami) pertimbangkan",
    r"kami akan (lihat|coba) dulu",
    r"mungkin (lain kali|nanti)",
]

_AVOIDANCE = [
    r"(ngomong|bicara|cerita) (tentang|soal) lain",
    r"oh ya (ngomong|bicara)-bicara",
    r"by the way", r"anyway",
    r"yang penting sekarang",
    r"let's talk about something else",
]

_IDENTITY_THREAT = [
    r"(bos|komisaris|direktur|direksi) (saya|kami)",
    r"nanti tanya (bos|atasan|pimpinan)",
    r"harus (lapor|konfirmasi|tanya) (dulu|ke) (bos|atasan)",
    r"saya (bukan|tidak) yang (memutuskan|berwenang)",
    r"as an expert", r"in my experience",
    r"I've been doing this for",
    r"you don't understand",
]

_HIGH_OPENNESS = [
    r"(kalau|jika|seandainya) (kita|kami) (bisa|mulai)",
    r"(bayangkan|imagine) (kalau|if)",
    r"(ke depan|kedepannya|masa depan)",
    r"(apa|how) (yang bisa|could) (kita|we) (lakukan|do)",
    r"tell me more", r"what if", r"how would",
    r"(kapan|when) (kita|could we) (mulai|start)",
    r"sounds interesting", r"menarik (juga|sekali)",
]

_CLOSING_DIRECT = [
    r"next steps?", r"move forward",
    r"who else (needs|should)",
    r"(let's|let us) (do|proceed|go ahead)",
    r"(I'm|we're) ready",
]

# Indonesian indirect closing signals — per PRD adversarial flags
_CLOSING_INDIRECT = [
    r"boleh minta proposal",
    r"kapan (bisa|kita) mulai",
    r"(kami|kita) tertarik",
    r"kirim (detail|penawaran|proposal)",
    r"berapa (biaya|harga|investasi)nya",
    r"apa (saja yang|yang perlu) (kami|kita) (siapkan|lakukan)",
]

_NEUTRAL = [
    r"(cerita|ceritakan) (lebih|dong)",
    r"(seperti apa|bagaimana) cara",
    r"(apa|what) (itu|is) (maksudnya|that)",
    r"tell me about", r"could you explain",
    r"how does (that|it) work",
]


def _match_any(text: str, patterns: list[str]) -> int:
    """Returns count of patterns matched in text."""
    count = 0
    t = text.lower()
    for p in patterns:
        if re.search(p, t):
            count += 1
    return count


class LocalClassifier:
    """
    Rule-based moment classifier. Fast (<10ms). Returns (MomentType, confidence).
    Confidence reflects signal strength — low confidence triggers SLM fallback.
    """

    CONFIDENCE_THRESHOLD = 0.4   # Below this → SLM fallback recommended

    def classify(
        self,
        text: str,
        elapsed_session_seconds: float = 999.0,
    ) -> tuple[MomentType, float]:
        """
        Classify a transcript segment.
        elapsed_session_seconds: used for basa-basi suppression in first 90s.
        Returns (MomentType, confidence 0.0–1.0).
        """
        if not text or not text.strip():
            return MomentType.NEUTRAL_EXPLORATORY, 0.3

        scores: dict[MomentType, float] = {mt: 0.0 for mt in MomentType}

        # Closing signal
        close_direct = _match_any(text, _CLOSING_DIRECT)
        close_indirect = _match_any(text, _CLOSING_INDIRECT)
        scores[MomentType.CLOSING_SIGNAL] = (close_direct * 0.8 + close_indirect * 0.9)

        # Irate/resistant — direct and indirect signals
        irate_direct = _match_any(text, _IRATE_DIRECT)
        irate_indirect = _match_any(text, _IRATE_INDIRECT)
        scores[MomentType.IRATE_RESISTANT] = (irate_direct * 1.0 + irate_indirect * 0.7)

        # Topic avoidance — suppressed in first 90s (basa-basi phase)
        avoidance = _match_any(text, _AVOIDANCE)
        if elapsed_session_seconds < 90.0:
            avoidance = 0  # basa-basi is not avoidance
        scores[MomentType.TOPIC_AVOIDANCE] = float(avoidance * 0.8)

        # Identity threat
        identity = _match_any(text, _IDENTITY_THREAT)
        scores[MomentType.IDENTITY_THREAT] = float(identity * 0.9)

        # High openness
        openness = _match_any(text, _HIGH_OPENNESS)
        scores[MomentType.HIGH_OPENNESS] = float(openness * 0.9)

        # Neutral exploratory
        neutral = _match_any(text, _NEUTRAL)
        scores[MomentType.NEUTRAL_EXPLORATORY] = float(neutral * 0.6 + 0.2)  # baseline

        # Pick highest score
        best = max(scores, key=lambda k: scores[k])
        best_score = scores[best]

        # Normalize to 0–1 confidence
        total = sum(scores.values())
        if total > 0:
            confidence = min(1.0, scores[best] / (total + 0.01))
        else:
            confidence = 0.3

        return best, confidence
