"""
Module: ecological_validator.py
Zone: 1 (Pre-session)
Input: Genome, market_context (str)
Output: list[PsychFlag] — ecological_validity type only
LLM calls: 0
Side effects: None
Latency tolerance: <50ms (pure rule-based lookup)

Indonesian B2B ecological validity checks. Returns flags when Western moment-type
classifier assumptions don't hold in Indonesian high-context B2B culture.
Only fires when market_context contains "Indonesia".
"""

from __future__ import annotations

from backend.genome.parameter_definitions import Genome
from backend.psych_review.validity_checker import PsychFlag


_ECOLOGICAL_FLAGS = [
    PsychFlag(
        flag_id="EF_001",
        type="ecological_validity",
        severity="HIGH",
        trait_or_moment="Irate/Resistant",
        concern=(
            "Resistance signals are short answers, elevated speech rate, direct topic dismissal. "
            "INCOMPATIBLE with Indonesian B2B: In Indonesian high-context B2B, resistance is encoded "
            "as sudden over-politeness, increased verbal affirmations (ya betul, tentu saja) without "
            "engagement, and topic deflection via counter-questions. Elevated speech rate is a Western "
            "signal — Indonesian resistance is often slower and more formal."
        ),
        practitioner_instruction=(
            "Watch for: increased formality, titles reappearing mid-conversation, sudden questions "
            "about unrelated topics, and extended 'yes-but' responses. If you detect this, do not "
            "escalate. Match the formality level and slow down. The prospect is managing face (malu) "
            "— give them space to exit discomfort without losing face."
        ),
    ),
    PsychFlag(
        flag_id="EF_002",
        type="ecological_validity",
        severity="HIGH",
        trait_or_moment="Closing/Signal",
        concern=(
            "Closing signals rely on explicit commitment language: 'next steps', 'who else needs "
            "to be involved', direct decision language. PARTIALLY INCOMPATIBLE: Indonesian closing "
            "signals are indirect. 'boleh minta proposal?' (can we get a proposal?) and 'kapan bisa "
            "mulai?' (when can you start?) are strong signals regardless of casual delivery. "
            "Direct 'I want to buy' is culturally rare."
        ),
        practitioner_instruction=(
            "Listen for proposal requests and timeline questions — these are the genuine buying "
            "signals. 'Iya, nanti kami coba pertimbangkan' (yes, we'll try to consider it) is the "
            "polite rejection, not a soft yes. Do not pursue it as a warm lead."
        ),
    ),
    PsychFlag(
        flag_id="EF_003",
        type="ecological_validity",
        severity="MODERATE",
        trait_or_moment="Topic/Avoidance",
        concern=(
            "Topic avoidance classifier looks for subject change and over-qualification. PARTIALLY "
            "COMPATIBLE: Extended basa-basi (social small talk) at session opening resembles topic "
            "avoidance in Western baseline. Basa-basi is culturally mandatory relationship maintenance, "
            "not avoidance. Requires prior topic context window to distinguish."
        ),
        practitioner_instruction=(
            "Do not intervene on topic avoidance signals in the first 5–8 minutes of conversation. "
            "This is basa-basi. Let it run. Premature redirection to business is face-threatening "
            "and signals that you prioritize transaction over relationship."
        ),
    ),
    PsychFlag(
        flag_id="EF_004",
        type="ecological_validity",
        severity="MODERATE",
        trait_or_moment="Identity/Threat",
        concern=(
            "Identity threat classifier looks for defensive language and explicit expertise appeals. "
            "PARTIALLY COMPATIBLE: In Indonesian B2B, identity threat manifests as seniority "
            "reference (nanti tanya bos dulu — I'll ask the boss first), formal title use, and "
            "third-party authority invocation. Explicit defensive language is culturally rare."
        ),
        practitioner_instruction=(
            "When you hear seniority deflection ('bos', 'komisaris', 'direksi'), recognize this as "
            "face-saving, not a genuine authority blocker. Acknowledge the hierarchy with respect, "
            "then re-anchor to the prospect's own role and expertise."
        ),
    ),
]


class EcologicalValidator:
    """
    Rule-based Indonesian B2B ecological validity checker.
    Only produces output when market_context indicates Indonesian B2B.
    """

    def check(self, genome: Genome, market_context: str) -> list[PsychFlag]:
        """
        Returns ecological validity flags for Indonesian B2B context.
        Returns empty list if market_context is not Indonesian B2B.
        """
        if "indonesia" not in market_context.lower():
            return []

        flags = list(_ECOLOGICAL_FLAGS)

        # Additional flag if agreeableness is low — direct confrontation risk in Indonesian context
        if genome.agreeableness is not None and genome.agreeableness < 45:
            flags.append(PsychFlag(
                flag_id="EF_005",
                type="ecological_validity",
                severity="MODERATE",
                trait_or_moment="agreeableness+Indonesian_face",
                concern=(
                    f"agreeableness={genome.agreeableness} (<45) in an Indonesian high-context context. "
                    "Low agreeableness dialog options may include direct challenge or confrontation "
                    "patterns that are face-threatening in Indonesian B2B."
                ),
                practitioner_instruction=(
                    "Avoid any dialog options that involve direct challenge or contradiction. "
                    "Frame all pushback as curious inquiry. Muka (face) is a primary social regulator "
                    "— loss of face triggers immediate disengagement."
                ),
            ))

        return flags
