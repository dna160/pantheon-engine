import os
from src.utils import DIVIDER

NODE5_SYSTEM = (
    "You are PANTHEON — the Team Lead and chief synthesis intelligence for a qualitative "
    "research firm specialising in Indonesian consumer psychology.\n\n"
    "You receive: (1) Phase A mass reaction data from multiple agents, "
    "(2) Phase B debate transcripts from focus group breakout rooms.\n\n"
    "Your output is the final Research Intelligence Report. "
    "Be incisive, specific, and actionable. No filler. No hedging. "
    "Write like a brilliant strategist, not a consultant. "
    "Reference specific agents, direct quotes, and data points from the input."
)

REPORT_PROMPT = """\
Generate the PANTHEON Research Intelligence Report with EXACTLY these 7 sections:

## 01. THE HEADLINE TRUTH
One brutal, specific sentence capturing the single most important consumer truth revealed.
Not a finding — a truth.

## 02. PTM SIGNAL ANALYSIS (Primary Target Market)
Who actually responded positively? Define the PTM precisely from the data.
What specific emotional and financial conditions make someone receptive?
Quote and cite specific agents with their age and demographic.

## 03. STM SIGNAL ANALYSIS (Secondary Target Market)
Who showed unexpected or conditional interest?
What specific trigger would convert them? Be precise.

## 04. THE FRACTURE LINES
What were the deepest points of disagreement in the focus group debates?
Identify 2-3 specific fault lines. What does each side's position reveal about their psychology?

## 05. THE INVISIBLE INSIGHT
What did the agents NOT say directly but reveal through their behavior, word choice,
and emotional temperature? This is the insight the brand would miss reading only surface data.

## 06. THREE SHARPENING RECOMMENDATIONS
Three specific, actionable campaign changes. Each must reference specific agent reactions as evidence.
Format: [RECOMMENDATION] → [EVIDENCE] → [EXPECTED RESPONSE SHIFT]

## 07. THE KILL SWITCH
What is the single biggest risk that could make this campaign backfire catastrophically?
Name it precisely. Who is most at risk of becoming an active detractor and why?\
"""


def node5_synthesis(mass_reactions: list[dict], breakout_transcripts: list[dict], campaign_brief: str) -> str:
    import anthropic as _anthropic
    client = _anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    # Phase A summary — rich format with emotion/temperature/relevance scores
    phase_a_lines = []
    for r in mass_reactions:
        if r.get("status") != "ok" or not r.get("phase_a"):
            continue
        pa = r["phase_a"]
        phase_a_lines.append(
            f"Agent Age {r.get('age')} ({r.get('demographic', r.get('target_demographic', 'Unknown'))}):\n"
            f"  Emotion={pa.get('dominant_emotion')} | Temp={pa.get('emotional_temperature')}/10 | "
            f"Relevance={pa.get('personal_relevance_score')}/10 | Intent={pa.get('intent_signal')}\n"
            f"  Gut reaction: \"{pa.get('gut_reaction')}\""
        )

    # Phase B transcripts — include participant ages
    phase_b_lines = []
    for tb in breakout_transcripts:
        if not tb.get("transcript"):
            phase_b_lines.append(f"[Group transcript unavailable — {tb.get('error', 'unknown error')}]")
        else:
            ages = ", ".join(str(a) for a in tb.get("participant_ages", []))
            phase_b_lines.append(
                f"GROUP (Ages: {ages}):\n{tb['transcript']}"
            )

    payload = (
        f"CAMPAIGN BRIEF:\n{campaign_brief}\n\n"
        f"{DIVIDER}\n"
        f"PHASE A — MASS SESSION RESULTS ({len(phase_a_lines)} agents):\n\n"
        + "\n\n".join(phase_a_lines)
        + f"\n\n{DIVIDER}\n"
        f"PHASE B — BREAKOUT ROOM TRANSCRIPTS:\n\n"
        + f"\n\n{'─'*50}\n\n".join(phase_b_lines)
        + f"\n\n{DIVIDER}\n\n"
        + REPORT_PROMPT
    )

    messages = [{"role": "user", "content": payload}]
    final_report = ""

    while True:
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=8192,
            system=NODE5_SYSTEM,
            messages=messages,
        )
        chunk_text = resp.content[0].text if resp.content else ""
        final_report += chunk_text
        if resp.stop_reason != "max_tokens":
            break
        messages.append({"role": "assistant", "content": chunk_text})
        messages.append({"role": "user", "content": "Continue writing the report from where you left off."})

    return final_report
