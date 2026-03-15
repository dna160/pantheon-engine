"""
test_full_pipeline.py — PANTHEON Full Execution Engine
Nodes 1 → 3 → 4 → 5 (Phase A → Phase B → Phase C)

Node 1: Query 10 agents from Supabase
Node 3: Phase A — 10 parallel Haiku calls (gut reactions)
Node 4: Phase B — 2 parallel Sonnet calls (breakout room debates, 5 agents each)
Node 5: Phase C — 1 final Sonnet call (Research Intelligence Report)
"""
import os
import json
import asyncio
from dotenv import load_dotenv
from supabase import create_client
import anthropic

load_dotenv("pantheon.env", override=True)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

if not SUPABASE_URL or not SUPABASE_KEY or not ANTHROPIC_API_KEY:
    print("ERROR: Missing credentials in pantheon.env")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
haiku = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
sonnet = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

# ────────────────────────────────────────────────────────────────────────────
# SHARED CONSTANTS
# ────────────────────────────────────────────────────────────────────────────

CAMPAIGN_BRIEF = (
    "A fintech app displays an iPhone advertisement for a Buy-Now-Pay-Later fintech app "
    "that lets users split rent payments into 4 installments in Indonesia."
)

DIVIDER = "═" * 70
THIN    = "─" * 70

# ────────────────────────────────────────────────────────────────────────────
# NODE 3 — PHASE A: The Mass Session
# ────────────────────────────────────────────────────────────────────────────

PHASE_A_TOOL = {
    "name": "submit_phase_a_reaction",
    "description": "Submit this agent's immediate gut reaction. All fields mandatory.",
    "input_schema": {
        "type": "object",
        "properties": {
            "gut_reaction": {
                "type": "string",
                "description": "1 sentence: the agent's visceral first reaction to the ad."
            },
            "emotional_temperature": {
                "type": "integer",
                "description": "1 (cold) to 10 (highly activated)."
            },
            "dominant_emotion": {
                "type": "string",
                "description": "Single word or short phrase."
            },
            "personal_relevance_score": {
                "type": "integer",
                "description": "1 (irrelevant) to 10 (directly speaks to my life)."
            },
            "intent_signal": {
                "type": "string",
                "description": "One of: ignore, glance, click, save, share, complain, dismiss."
            }
        },
        "required": [
            "gut_reaction", "emotional_temperature", "dominant_emotion",
            "personal_relevance_score", "intent_signal"
        ],
        "additionalProperties": False
    }
}

PHASE_A_SYSTEM = (
    "You are PANTHEON Phase A Engine. Simulate the exact immediate reaction of a specific "
    "Indonesian consumer agent when they encounter an ad on their phone.\n"
    "Stay fully in character. The reaction must be psychologically consistent with "
    "their personality integers, life history, financial situation, and Medanese cultural background.\n"
    "Do NOT generate a generic consumer response. This is a specific human with a specific history."
)


def build_agent_context(agent: dict) -> str:
    """Compact agent context for prompt injection."""
    genome = (
        f"Genome: O={agent.get('openness')} C={agent.get('conscientiousness')} "
        f"E={agent.get('extraversion')} A={agent.get('agreeableness')} N={agent.get('neuroticism')} | "
        f"CommStyle={agent.get('communication_style')} Dec={agent.get('decision_making')} "
        f"Brand={agent.get('brand_relationship')} Influ={agent.get('influence_susceptibility')} "
        f"EmotExp={agent.get('emotional_expression')} Conflict={agent.get('conflict_behavior')}"
    )

    age = agent.get("age", 30)
    if age <= 28:
        layer = agent.get("formation_layer") or agent.get("independence_layer")
    elif age <= 38:
        layer = agent.get("independence_layer") or agent.get("maturity_layer")
    else:
        layer = agent.get("maturity_layer") or agent.get("legacy_layer")

    layer_text = ""
    if isinstance(layer, dict):
        layer_text = (
            f"\nLife Stage: {layer.get('summary', '')}"
            f"\nPsychological profile: {layer.get('psychological_impact', '')}"
        )

    vp = agent.get("voice_print") or {}
    triggers = ""
    if isinstance(vp, dict) and vp.get("persuasion_triggers"):
        triggers = f"\nPersuasion triggers: {', '.join(vp['persuasion_triggers'])}"

    return (
        f"Age: {agent.get('age')} | Demographic: {agent.get('target_demographic')}\n"
        f"{genome}{layer_text}{triggers}"
    )


async def run_phase_a_for_agent(agent: dict, index: int) -> dict:
    ctx = build_agent_context(agent)
    msg = (
        f"{ctx}\n\n"
        f"Campaign stimulus: {CAMPAIGN_BRIEF}\n\n"
        "Simulate this agent's immediate gut reaction."
    )
    try:
        resp = await haiku.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            system=PHASE_A_SYSTEM,
            tools=[PHASE_A_TOOL],
            tool_choice={"type": "tool", "name": "submit_phase_a_reaction"},
            messages=[{"role": "user", "content": msg}]
        )
        block = next((b for b in resp.content if b.type == "tool_use"), None)
        if not block:
            raise ValueError("No tool_use block")
        return {
            "agent_index": index,
            "agent_id": agent.get("id"),
            "age": agent.get("age"),
            "demographic": agent.get("target_demographic"),
            "agent_context": ctx,
            "phase_a": block.input,
            "status": "ok"
        }
    except Exception as e:
        return {
            "agent_index": index,
            "agent_id": agent.get("id"),
            "age": agent.get("age"),
            "demographic": agent.get("target_demographic"),
            "agent_context": ctx,
            "phase_a": None,
            "status": "error",
            "error": str(e)
        }


# ────────────────────────────────────────────────────────────────────────────
# NODE 4 — PHASE B: The Breakout Rooms
# ────────────────────────────────────────────────────────────────────────────

PHASE_B_SYSTEM = (
    "You are a qualitative research director facilitating a focus group simulation. "
    "You have deep knowledge of Indonesian culture, Medanese social dynamics, "
    "Batak/Hokkien/Minangkabau psychology, and fintech consumer behavior.\n\n"
    "Your task: Simulate how THESE SPECIFIC PEOPLE actually talk — not generic consumers. "
    "Use their personality scores, cultural backgrounds, and financial realities. "
    "Let them interrupt, challenge each other, go off-topic, and be themselves. "
    "Do not force consensus or resolution."
)


def build_group_context(group: list[dict]) -> str:
    """Render a group of 5 agents + their Phase A reactions for the Sonnet prompt."""
    parts = []
    for r in group:
        pa = r.get("phase_a") or {}
        parts.append(
            f"PARTICIPANT {r['agent_index']} (Age {r['age']}, {r['demographic']})\n"
            f"Profile: {r['agent_context']}\n"
            f"Initial gut reaction: \"{pa.get('gut_reaction', 'N/A')}\"\n"
            f"Dominant emotion: {pa.get('dominant_emotion', 'N/A')} | "
            f"Emotional temp: {pa.get('emotional_temperature', 'N/A')}/10 | "
            f"Relevance: {pa.get('personal_relevance_score', 'N/A')}/10 | "
            f"Intent: {pa.get('intent_signal', 'N/A')}"
        )
    return "\n\n".join(parts)


async def run_phase_b_for_group(group: list[dict], group_num: int) -> dict:
    """Fire one Sonnet call to simulate a 15-turn breakout room debate."""
    group_ctx = build_group_context(group)
    agent_nums = [str(r["agent_index"]) for r in group]

    msg = (
        f"CAMPAIGN BRIEF:\n{CAMPAIGN_BRIEF}\n\n"
        f"{'─' * 50}\n"
        f"FOCUS GROUP PARTICIPANTS (Group {group_num}):\n\n"
        f"{group_ctx}\n\n"
        f"{'─' * 50}\n"
        f"INSTRUCTIONS:\n"
        f"These 5 people (Participants {', '.join(agent_nums)}) have just seen the ad above "
        f"and shared their initial reactions. Now they are in a focus group breakout room together.\n\n"
        f"Write a raw, realistic 15-turn debate transcript where they discuss this fintech app. "
        f"Rules:\n"
        f"- Speak in their authentic voice (vocabulary level, filler words, cultural references)\n"
        f"- Let them interrupt, disagree, go off on tangents\n"
        f"- They must reference their specific financial realities and cultural backgrounds\n"
        f"- Do NOT force consensus — real focus groups are messy\n"
        f"- Label each turn as: PARTICIPANT [N]: [dialogue]\n"
        f"- Make it feel like a real conversation, not a debate club"
    )

    try:
        resp = await sonnet.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=2500,
            system=PHASE_B_SYSTEM,
            messages=[{"role": "user", "content": msg}]
        )
        transcript = resp.content[0].text
        return {
            "group_num": group_num,
            "participant_indices": agent_nums,
            "transcript": transcript,
            "status": "ok"
        }
    except Exception as e:
        return {
            "group_num": group_num,
            "participant_indices": agent_nums,
            "transcript": None,
            "status": "error",
            "error": str(e)
        }


async def run_phase_b(phase_a_results: list[dict]) -> list[dict]:
    """Split 10 results into 2 groups of 5, fire debates in parallel."""
    valid = [r for r in phase_a_results if r["status"] == "ok"]
    group_1 = valid[:5]
    group_2 = valid[5:10]

    tasks = [
        run_phase_b_for_group(group_1, 1),
        run_phase_b_for_group(group_2, 2),
    ]
    return await asyncio.gather(*tasks)


# ────────────────────────────────────────────────────────────────────────────
# NODE 5 — PHASE C: Synthesis (The PANTHEON Report)
# ────────────────────────────────────────────────────────────────────────────

PHASE_C_SYSTEM = (
    "You are PANTHEON — the Team Lead and chief synthesis intelligence for a qualitative "
    "research firm specialising in Indonesian consumer psychology.\n\n"
    "You receive: (1) Phase A mass reaction data from 10 agents, "
    "(2) Phase B debate transcripts from 2 focus group breakout rooms.\n\n"
    "Your output is the final Research Intelligence Report. "
    "It must be incisive, specific, and actionable. "
    "No filler. No hedging. Write like a brilliant strategist, not a consultant. "
    "Reference specific agents, quotes, and data points from the input."
)

PHASE_C_REPORT_SECTIONS = (
    "Generate the PANTHEON Research Intelligence Report with EXACTLY these 7 sections:\n\n"
    "1. THE HEADLINE TRUTH\n"
    "   One brutal, specific sentence that captures the single most important consumer truth "
    "   revealed by this study. Not a finding — a truth.\n\n"
    "2. PTM SIGNAL ANALYSIS (Primary Target Market)\n"
    "   Who actually responded? Define the PTM precisely from the data. "
    "   What specific emotional and financial conditions make someone receptive? "
    "   Quote and cite specific agents.\n\n"
    "3. STM SIGNAL ANALYSIS (Secondary Target Market)\n"
    "   Who showed unexpected or conditional interest? "
    "   What specific trigger would convert them? Be precise.\n\n"
    "4. THE FRACTURE LINES\n"
    "   What were the deepest points of disagreement in the focus group debates? "
    "   Identify 2-3 specific fault lines. What does each side's position reveal about their psychology?\n\n"
    "5. THE INVISIBLE INSIGHT\n"
    "   What did the agents NOT say directly but reveal through their behavior, "
    "   word choice, and emotional temperature? "
    "   This is the insight the brand would miss if they only read the surface data.\n\n"
    "6. THREE SHARPENING RECOMMENDATIONS\n"
    "   Three specific, actionable changes to the campaign. "
    "   Each must reference specific agent reactions as evidence. "
    "   Format: [RECOMMENDATION] → [EVIDENCE] → [EXPECTED RESPONSE SHIFT]\n\n"
    "7. THE KILL SWITCH\n"
    "   What is the single biggest risk that could make this campaign backfire? "
    "   Name it precisely. Who is most at risk of becoming an active detractor and why?"
)


async def run_phase_c(phase_a_results: list[dict], phase_b_transcripts: list[dict]) -> str:
    """Fire the single synthesis call. Returns the full PANTHEON report as a string."""

    # Build Phase A summary
    phase_a_summary = []
    for r in phase_a_results:
        if r["status"] != "ok":
            continue
        pa = r["phase_a"]
        phase_a_summary.append(
            f"Agent {r['agent_index']} (Age {r['age']}, {r['demographic']}): "
            f"Emotion={pa.get('dominant_emotion')} | Temp={pa.get('emotional_temperature')}/10 | "
            f"Relevance={pa.get('personal_relevance_score')}/10 | Intent={pa.get('intent_signal')}\n"
            f"  Gut reaction: \"{pa.get('gut_reaction')}\""
        )

    # Build Phase B summaries
    phase_b_sections = []
    for tb in phase_b_transcripts:
        if tb["status"] != "ok":
            phase_b_sections.append(
                f"[Group {tb['group_num']} transcript unavailable — error: {tb.get('error')}]"
            )
        else:
            phase_b_sections.append(
                f"GROUP {tb['group_num']} TRANSCRIPT "
                f"(Participants: {', '.join(tb['participant_indices'])}):\n"
                f"{tb['transcript']}"
            )

    msg = (
        f"CAMPAIGN BRIEF:\n{CAMPAIGN_BRIEF}\n\n"
        f"{DIVIDER}\n"
        f"PHASE A — MASS SESSION RESULTS (10 agents):\n\n"
        + "\n\n".join(phase_a_summary)
        + f"\n\n{DIVIDER}\n"
        f"PHASE B — BREAKOUT ROOM TRANSCRIPTS:\n\n"
        + f"\n\n{'─'*50}\n\n".join(phase_b_sections)
        + f"\n\n{DIVIDER}\n\n"
        + PHASE_C_REPORT_SECTIONS
    )

    resp = await sonnet.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=4000,
        system=PHASE_C_SYSTEM,
        messages=[{"role": "user", "content": msg}]
    )
    return resp.content[0].text


# ────────────────────────────────────────────────────────────────────────────
# MAIN ORCHESTRATOR
# ────────────────────────────────────────────────────────────────────────────

async def main():
    print(f"\n{DIVIDER}")
    print("  PANTHEON — Full Pipeline Test (Nodes 1 → 3 → 4 → 5)")
    print(f"{DIVIDER}")
    print(f"  Brief: {CAMPAIGN_BRIEF[:75]}...")
    print(f"{DIVIDER}\n")

    # ── Node 1: Query Supabase ──────────────────────────────────────────────
    print("NODE 1 ─ Querying Supabase for 10 agents...")
    db_result = supabase.table("agent_genomes").select("*").limit(10).execute()
    agents = db_result.data
    if not agents:
        print("  ERROR: No agents found. Run seed_genomes.py first.")
        return
    print(f"  ✓ Pulled {len(agents)} agents.\n")

    # ── Node 3: Phase A ─────────────────────────────────────────────────────
    print(f"NODE 3 ─ Phase A: Firing {len(agents)} parallel Haiku calls...")
    phase_a_tasks = [
        run_phase_a_for_agent(agent, i + 1)
        for i, agent in enumerate(agents)
    ]
    phase_a_results = list(await asyncio.gather(*phase_a_tasks))
    ok_a = sum(1 for r in phase_a_results if r["status"] == "ok")
    print(f"  ✓ Phase A complete: {ok_a}/{len(agents)} agents responded.\n")

    # Print Phase A summary
    for r in phase_a_results:
        pa = r.get("phase_a") or {}
        status = "✓" if r["status"] == "ok" else "✗"
        print(
            f"  {status} Agent {r['agent_index']:02d} | Age {r['age']} | "
            f"Emotion: {pa.get('dominant_emotion', 'ERROR')} | "
            f"Temp: {pa.get('emotional_temperature', '-')}/10 | "
            f"Intent: {pa.get('intent_signal', '-')}"
        )
    print()

    # ── Node 4: Phase B ─────────────────────────────────────────────────────
    print("NODE 4 ─ Phase B: Firing 2 parallel Sonnet breakout room debates...")
    print("  (Group 1 = Agents 1-5 | Group 2 = Agents 6-10)")
    phase_b_results = await run_phase_b(phase_a_results)
    ok_b = sum(1 for r in phase_b_results if r["status"] == "ok")
    print(f"  ✓ Phase B complete: {ok_b}/2 transcripts generated.\n")

    # Print Phase B transcripts
    for tb in phase_b_results:
        print(f"{DIVIDER}")
        print(f"  PHASE B — GROUP {tb['group_num']} TRANSCRIPT")
        print(f"{DIVIDER}")
        if tb["status"] == "ok":
            print(tb["transcript"])
        else:
            print(f"  ERROR: {tb.get('error')}")
        print()

    # ── Node 5: Phase C ─────────────────────────────────────────────────────
    print(f"{DIVIDER}")
    print("NODE 5 ─ Phase C: Firing Phase C synthesis (claude-sonnet-4-5)...")
    print(f"{DIVIDER}\n")

    report = await run_phase_c(phase_a_results, phase_b_results)

    print(f"\n{'═'*70}")
    print("  PANTHEON RESEARCH INTELLIGENCE REPORT")
    print(f"{'═'*70}\n")
    print(report)
    print(f"\n{'═'*70}")
    print("  END OF REPORT")
    print(f"{'═'*70}\n")


if __name__ == "__main__":
    asyncio.run(main())
