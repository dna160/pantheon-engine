"""
test_phase_a.py — PANTHEON Node 3: Phase A (The Mass Session)
Pulls 10 agents from Supabase, fires 10 parallel async Claude Haiku calls,
enforces structured output via Anthropic tool_choice, prints results.
"""
import os
import json
import asyncio
from dotenv import load_dotenv
from supabase import create_client
import anthropic

load_dotenv('pantheon.env', override=True)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

if not SUPABASE_URL or not SUPABASE_KEY or not ANTHROPIC_API_KEY:
    print("ERROR: Missing credentials in pantheon.env")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
# AsyncAnthropic for native async/await support
client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

# ---------------------------------------------------------------------------
# Campaign brief
# ---------------------------------------------------------------------------

CAMPAIGN_BRIEF = (
    "A fintech app displays an iPhone advertisement for a Buy-Now-Pay-Later fintech app "
    "that lets users split rent payments into 4 installments in Indonesia."
)

# ---------------------------------------------------------------------------
# Tool schema: enforces exact Phase A output structure
# ---------------------------------------------------------------------------

PHASE_A_TOOL = {
    "name": "submit_phase_a_reaction",
    "description": (
        "Submit this agent's immediate gut reaction to the campaign stimulus. "
        "All fields are mandatory."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "gut_reaction": {
                "type": "string",
                "description": "1 sentence: the agent's immediate, visceral first reaction to the ad."
            },
            "emotional_temperature": {
                "type": "integer",
                "description": "1 (completely cold/unresponsive) to 10 (highly emotionally activated)."
            },
            "dominant_emotion": {
                "type": "string",
                "description": "Single word or short phrase: e.g. 'skepticism', 'relief', 'anxiety', 'curiosity'."
            },
            "personal_relevance_score": {
                "type": "integer",
                "description": "1 (completely irrelevant to my life) to 10 (directly speaks to my situation)."
            },
            "intent_signal": {
                "type": "string",
                "description": "One of: 'ignore', 'glance', 'click', 'save', 'share', 'complain', 'dismiss'."
            }
        },
        "required": [
            "gut_reaction",
            "emotional_temperature",
            "dominant_emotion",
            "personal_relevance_score",
            "intent_signal"
        ],
        "additionalProperties": False
    }
}

# ---------------------------------------------------------------------------
# System prompt — lean but enough cultural + psychological grounding
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are PANTHEON Phase A Engine. You simulate the exact immediate reaction of a "
    "specific Indonesian consumer agent when they encounter an advertisement on their phone.\n\n"
    "You are given:\n"
    "1. The agent's immutable DNA: their personality genome (integer scores) and 100-year life blueprint.\n"
    "2. The campaign stimulus they just encountered.\n\n"
    "Your task: Simulate this specific person's gut-level, sub-3-second reaction to the ad. "
    "Stay fully in character. The reaction must be psychologically consistent with: "
    "their personality integers, their life history, their financial situation, "
    "and their cultural background (Medanese upper-middle class).\n\n"
    "Do NOT generate a generic consumer response. This is a specific human with a specific history."
)


def build_agent_context(agent: dict) -> str:
    """Render the agent's genome into a compact context string for the prompt."""
    genome_lines = (
        f"Personality Genome (1-100 scale):\n"
        f"  Openness={agent.get('openness')} | Conscientiousness={agent.get('conscientiousness')} | "
        f"Extraversion={agent.get('extraversion')} | Agreeableness={agent.get('agreeableness')} | "
        f"Neuroticism={agent.get('neuroticism')}\n"
        f"  CommunicationStyle={agent.get('communication_style')} | DecisionMaking={agent.get('decision_making')} | "
        f"BrandRelationship={agent.get('brand_relationship')} | InfluenceSusceptibility={agent.get('influence_susceptibility')} | "
        f"EmotionalExpression={agent.get('emotional_expression')} | ConflictBehavior={agent.get('conflict_behavior')}"
    )

    # Pull the most relevant life layer based on age
    age = agent.get('age', 30)
    if age <= 18:
        relevant_layer = agent.get('origin_layer') or agent.get('formation_layer')
    elif age <= 28:
        relevant_layer = agent.get('formation_layer') or agent.get('independence_layer')
    elif age <= 38:
        relevant_layer = agent.get('independence_layer') or agent.get('maturity_layer')
    else:
        relevant_layer = agent.get('maturity_layer') or agent.get('legacy_layer')

    layer_text = ""
    if isinstance(relevant_layer, dict):
        layer_text = (
            f"\nCurrent Life Stage Context:\n"
            f"  {relevant_layer.get('summary', '')}\n"
            f"  Psychological impact: {relevant_layer.get('psychological_impact', '')}"
        )

    voice_print = agent.get('voice_print') or {}
    triggers_text = ""
    if isinstance(voice_print, dict) and voice_print.get('persuasion_triggers'):
        triggers = voice_print['persuasion_triggers']
        triggers_text = f"\nPersuasion Triggers: {', '.join(triggers)}"

    return (
        f"AGENT PROFILE\n"
        f"═════════════\n"
        f"Demographic: {agent.get('target_demographic', 'Unknown')}\n"
        f"Age: {agent.get('age')} | Region: {agent.get('region', 'Medan, Indonesia')}\n\n"
        f"{genome_lines}"
        f"{layer_text}"
        f"{triggers_text}"
    )


async def run_phase_a_for_agent(agent: dict, index: int) -> dict:
    """
    Fire one async Phase A call for a single agent.
    Returns a result dict with agent metadata + Phase A output.
    """
    agent_context = build_agent_context(agent)

    user_message = (
        f"{agent_context}\n\n"
        f"CAMPAIGN STIMULUS\n"
        f"═════════════════\n"
        f"{CAMPAIGN_BRIEF}\n\n"
        f"Simulate this agent's immediate gut reaction to this ad."
    )

    try:
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            system=SYSTEM_PROMPT,
            tools=[PHASE_A_TOOL],
            tool_choice={"type": "tool", "name": "submit_phase_a_reaction"},
            messages=[{"role": "user", "content": user_message}]
        )

        block = next((b for b in response.content if b.type == "tool_use"), None)
        if block is None:
            raise ValueError("No tool_use block in response")

        result = block.input
        return {
            "agent_index": index,
            "agent_id": agent.get("id", "unknown"),
            "age": agent.get("age"),
            "demographic": agent.get("target_demographic"),
            "phase_a": result,
            "status": "ok"
        }

    except Exception as e:
        return {
            "agent_index": index,
            "agent_id": agent.get("id", "unknown"),
            "age": agent.get("age"),
            "demographic": agent.get("target_demographic"),
            "phase_a": None,
            "status": "error",
            "error": str(e)
        }


async def main():
    print("\n═══ PANTHEON — Node 3: Phase A (Mass Session) ═══")
    print(f"Campaign: {CAMPAIGN_BRIEF[:80]}...")
    print()

    # --- Node 1: Query Supabase ---
    print("Querying Supabase for 10 agents...")
    result = supabase.table("agent_genomes").select("*").limit(10).execute()
    agents = result.data

    if not agents:
        print("ERROR: No agents found in database. Run seed_genomes.py first.")
        return

    print(f"  Pulled {len(agents)} agents from DB.\n")

    # --- Node 3: Fire 10 parallel async calls ---
    print(f"Firing {len(agents)} parallel Phase A calls (claude-haiku-4-5-20251001)...")
    print("─" * 60)

    tasks = [
        run_phase_a_for_agent(agent, i + 1)
        for i, agent in enumerate(agents)
    ]
    results = await asyncio.gather(*tasks)

    # --- Print results ---
    print()
    success_count = sum(1 for r in results if r["status"] == "ok")
    print(f"═══ Phase A Complete: {success_count}/{len(agents)} agents responded ═══\n")

    for r in results:
        print(f"Agent {r['agent_index']:02d} | Age {r['age']} | {r['demographic']}")
        if r["status"] == "ok":
            pa = r["phase_a"]
            print(f"  Gut Reaction    : {pa.get('gut_reaction')}")
            print(f"  Dominant Emotion: {pa.get('dominant_emotion')}")
            print(f"  Emotional Temp  : {pa.get('emotional_temperature')}/10")
            print(f"  Relevance Score : {pa.get('personal_relevance_score')}/10")
            print(f"  Intent Signal   : {pa.get('intent_signal')}")
        else:
            print(f"  ✗ ERROR: {r.get('error')}")
        print()

    # Print raw JSON for verification
    print("─" * 60)
    print("RAW JSON OUTPUT:")
    print("─" * 60)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
