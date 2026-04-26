"""
Module: delta_classifier.py
Zone: 1 (Pre-session)
Input: prospect_id, post dict, source str
Output: DeltaSignal | None (None for NEUTRAL posts)
LLM calls: 0  — rule-based keyword matching, <1s on any device
Side effects: None
Latency tolerance: <1 second total for all posts

Classifies each new social post into a DeltaSignalType.
Part of the Signal Delta pipeline. Imported by delta_pipeline.py facade.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import structlog

from backend.genome.parameter_definitions import (
    DeltaSignal,
    DeltaSignalType,
)

logger = structlog.get_logger(__name__)


class DeltaClassifier:
    """
    Classifies each new social post into a DeltaSignalType.
    Rule-based. No LLM. Runs in <1 second on any device.
    Supports Bahasa Indonesia keywords alongside English.
    """

    # Keyword sets for classification
    VALIDATION_KEYWORDS = {
        "promoted", "promotion", "award", "winner", "milestone", "achievement",
        "launched", "closing", "closed deal", "new role", "excited to announce",
        "dipromosikan", "penghargaan", "pencapaian", "peluncuran", "peran baru",
        "senang mengumumkan",
    }
    FRICTION_KEYWORDS = {
        "challenging", "difficult", "struggle", "setback", "layoff", "let go",
        "uncertain", "tough", "resign", "quit",
        "sulit", "tantangan", "perjuangan", "mundur", "keluar", "tidak pasti",
    }
    MOMENTUM_KEYWORDS = {
        "new venture", "starting", "building", "excited", "opportunity",
        "future", "vision", "growth", "expanding",
        "usaha baru", "mulai", "membangun", "bersemangat", "peluang",
        "masa depan", "visi", "pertumbuhan", "berkembang",
    }
    CONSOLIDATION_KEYWORDS = {
        "defending", "protecting", "staying", "stable", "cautious",
        "not changing", "same team", "committed to current",
        "bertahan", "melindungi", "tetap", "stabil", "hati-hati",
    }

    def classify(
        self,
        prospect_id: str,
        post: dict[str, Any],
        source: str,
    ) -> DeltaSignal | None:
        """
        Classifies a single post. Returns None for NEUTRAL (no display needed).
        """
        text = (post.get("text", "") + " " + post.get("caption", "")).lower()
        timestamp_str = post.get("timestamp", datetime.now(timezone.utc).isoformat())

        try:
            detected_at = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            detected_at = datetime.now(timezone.utc)

        signal_type, rwi_impact, display_msg = self._classify_text(text, detected_at)

        if signal_type == DeltaSignalType.NEUTRAL:
            return None

        return DeltaSignal(
            prospect_id=prospect_id,
            signal_type=signal_type,
            source=source,
            detected_at=detected_at,
            content_summary=text[:120] + "..." if len(text) > 120 else text,
            rwi_impact=rwi_impact,
            display_message=display_msg,
        )

    def _classify_text(
        self, text: str, detected_at: datetime
    ) -> tuple[DeltaSignalType, int, str]:
        words = set(text.split())
        days_ago = (datetime.now(timezone.utc) - detected_at).days

        validation_hits = len(words & self.VALIDATION_KEYWORDS)
        friction_hits = len(words & self.FRICTION_KEYWORDS)
        momentum_hits = len(words & self.MOMENTUM_KEYWORDS)
        consolidation_hits = len(words & self.CONSOLIDATION_KEYWORDS)

        # Dominance check — highest hit count wins
        scores = {
            DeltaSignalType.VALIDATION_EVENT: validation_hits,
            DeltaSignalType.FRICTION_SIGNAL: friction_hits,
            DeltaSignalType.IDENTITY_MOMENTUM: momentum_hits,
            DeltaSignalType.CONSOLIDATION: consolidation_hits,
        }

        max_type = max(scores, key=scores.__getitem__)
        max_score = scores[max_type]

        if max_score == 0:
            return DeltaSignalType.NEUTRAL, 0, ""

        # RWI impact and display message per type
        if max_type == DeltaSignalType.VALIDATION_EVENT:
            rwi_impact = min(20, max(5, 15 - days_ago))
            msg = f"Validation post {days_ago}d ago → RWI +{rwi_impact}"
        elif max_type == DeltaSignalType.FRICTION_SIGNAL:
            rwi_impact = -min(20, max(5, 15 - days_ago))
            msg = f"Friction signal {days_ago}d ago → RWI {rwi_impact}"
        elif max_type == DeltaSignalType.IDENTITY_MOMENTUM:
            rwi_impact = min(15, max(3, 12 - days_ago))
            msg = f"Identity expansion signal {days_ago}d ago → RWI +{rwi_impact}"
        else:  # CONSOLIDATION
            rwi_impact = -min(10, max(2, 8 - days_ago))
            msg = f"Consolidation signal {days_ago}d ago → RWI {rwi_impact}"

        return max_type, rwi_impact, msg
