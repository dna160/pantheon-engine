"""
PANTHEON Genesis Builder — seed_genomes.py
Generates 5 distinct agent profiles for 'Medanese Upper Middle Class, 25-45'

Cost strategy (~$0.05/agent):
  - TWO small tool calls per agent instead of one large one:
      Call 1: Personality integers (11 fields) + voice_print (~300 output tokens)
      Call 2: 5 life blueprint layers (~600 output tokens)
  - Schema passed as Anthropic Tool definition (not in prompt text) → minimal input tokens
  - Lean system prompt, capped narrative lengths
  - 65s sleep between agents → no rate limit errors
"""
import os
import time
import uuid
from datetime import datetime, timezone
from dotenv import load_dotenv
from supabase import create_client, Client
import anthropic

from genome_culture import generate_base_genome, apply_age_drift

load_dotenv('pantheon.env', override=True)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

if not SUPABASE_URL or not SUPABASE_KEY or not ANTHROPIC_API_KEY:
    print("ERROR: Missing credentials in pantheon.env")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# ---------------------------------------------------------------------------
# TOOL 1: Personality genome (integers + voice print)
# ~300 output tokens
# ---------------------------------------------------------------------------

GENOME_TOOL = {
    "name": "submit_genome",
    "description": "Submit all personality integer scores and voice print. ALL fields required.",
    "input_schema": {
        "type": "object",
        "properties": {
            "openness":                {"type": "integer", "description": "1=closed-minded, 100=experimental"},
            "conscientiousness":       {"type": "integer", "description": "1=impulsive, 100=methodical"},
            "extraversion":            {"type": "integer", "description": "1=introvert, 100=extrovert"},
            "agreeableness":           {"type": "integer", "description": "1=adversarial, 100=cooperative"},
            "neuroticism":             {"type": "integer", "description": "1=stable, 100=anxious"},
            "communication_style":     {"type": "integer", "description": "1=indirect, 100=direct"},
            "decision_making":         {"type": "integer", "description": "1=gut-driven, 100=data-driven"},
            "brand_relationship":      {"type": "integer", "description": "1=price-driven, 100=brand-loyal"},
            "influence_susceptibility":{"type": "integer", "description": "1=impervious, 100=susceptible"},
            "emotional_expression":    {"type": "integer", "description": "1=stoic, 100=openly emotional"},
            "conflict_behavior":       {"type": "integer", "description": "1=avoider, 100=confrontational"},
            "identity_fusion":         {"type": "integer", "description": "1=individualist, 100=visceral group fusion"},
            "chronesthesia_capacity":  {"type": "integer", "description": "1=present-only, 100=vivid mental time travel"},
            "tom_self_awareness":      {"type": "integer", "description": "1=blind to own states, 100=deep self-reflection"},
            "tom_social_modeling":     {"type": "integer", "description": "1=oblivious to others, 100=reads rooms perfectly"},
            "executive_flexibility":   {"type": "integer", "description": "1=traits leak always, 100=can override impulses"},
            "voice_print": {
                "type": "object",
                "properties": {
                    "vocabulary_level":    {"type": "string", "description": "How this person speaks (1 sentence)"},
                    "filler_words":        {"type": "array", "items": {"type": "string"}, "description": "3 filler words/phrases"},
                    "persuasion_triggers": {"type": "array", "items": {"type": "string"}, "description": "3 purchase triggers"},
                    "conflict_style":      {"type": "string", "description": "1 sentence on how they handle disagreement"}
                },
                "required": ["vocabulary_level", "filler_words", "persuasion_triggers", "conflict_style"],
                "additionalProperties": False
            }
        },
        "required": [
            "openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism",
            "communication_style", "decision_making", "brand_relationship",
            "influence_susceptibility", "emotional_expression", "conflict_behavior",
            "identity_fusion", "chronesthesia_capacity", "tom_self_awareness",
            "tom_social_modeling", "executive_flexibility",
            "voice_print"
        ],
        "additionalProperties": False
    }
}

# ---------------------------------------------------------------------------
# TOOL 2: Life blueprint (5 JSONB layers)
# ~600 output tokens
# ---------------------------------------------------------------------------

LAYER_DEFINITION = {
    "type": "object",
    "properties": {
        "summary":              {"type": "string", "description": "MAX 100 chars. 1 sentence only."},
        "key_events":           {"type": "array", "items": {"type": "string"}, "description": "Exactly 3 items, each MAX 60 chars"},
        "psychological_impact": {"type": "string", "description": "MAX 80 chars. 1 sentence only."}
    },
    "required": ["summary", "key_events", "psychological_impact"],
    "additionalProperties": False
}

BLUEPRINT_TOOL = {
    "name": "submit_blueprint",
    "description": "Submit all 5 life stage layers for the agent. ALL layers required.",
    "input_schema": {
        "type": "object",
        "properties": {
            "origin_layer":       LAYER_DEFINITION,
            "formation_layer":    LAYER_DEFINITION,
            "independence_layer": LAYER_DEFINITION,
            "maturity_layer":     LAYER_DEFINITION,
            "legacy_layer":       LAYER_DEFINITION,
        },
        "required": ["origin_layer", "formation_layer", "independence_layer", "maturity_layer", "legacy_layer"],
        "additionalProperties": False
    }
}

# ---------------------------------------------------------------------------
# System prompt — lean, cultural context only
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are PANTHEON Genesis Builder: generating psychologically coherent Medanese consumer profiles.\n"
    "Cultural context: Hokkien merchant culture (guanxi, mianzi), Batak Toba/Karo marga dynamics, "
    "Minangkabau matriarchal values, Sun Plaza as class marker, GrabFood/TikTok/Tokopedia adoption, "
    "aspirational tension between Medan identity and Jakarta cosmopolitanism.\n"
    "Rules: Every integer must be justified by the narrative. Keep ALL text fields brief. "
    "No generic descriptions — be culturally specific to Medan."
)

# ---------------------------------------------------------------------------
# Archetypes
# ---------------------------------------------------------------------------

ARCHETYPES = [
    {
        "age": 42,
        "seed": (
            "42-year-old Chinese-Indonesian Hokkien male. Third-generation wholesale textile merchant, "
            "Pasar Ikan Lama Medan, 25 employees. Temple weekly, clan association active. "
            "Conservative, status-conscious, Mercedes E-Class, Polo Ralph Lauren loyal. Never left Medan."
        )
    },
    {
        "age": 31,
        "seed": (
            "31-year-old Batak Toba female, corporate litigation attorney. "
            "USU law + LLM Jakarta (Tarumanagara). Returned for marga obligations. "
            "Feminist but adat-rooted. Heavy Instagram user, Sun Plaza shopper. Skeptical of ads, loves Zara/Sephora."
        )
    },
    {
        "age": 27,
        "seed": (
            "27-year-old Javanese-Medan male. Co-founder halal frozen food startup, GrabFood/Tokopedia. "
            "University dropout, TikTok creator 40K followers. Frugal personally, aggressive investor. "
            "Setia Budi kost. Buys only via WhatsApp peer recs. Aspirational but not yet arrived."
        )
    },
    {
        "age": 38,
        "seed": (
            "38-year-old Minangkabau female. Private dermatology clinic owner, Jalan Setia Budi Medan. "
            "Universitas Indonesia MD + Derm diplomate. Evidence-driven, La Roche-Posay only, rejects influencer skincare. "
            "Sends remittances West Sumatra. Slow decisions but extreme conviction once committed."
        )
    },
    {
        "age": 44,
        "seed": (
            "44-year-old Batak Karo male. Regional Sales Director, multinational FMCG, North Sumatra. "
            "Rose from field salesman. Sends children to Cambridge School Medan. Toyota Fortuner. "
            "Peer-influenced, replicates Jakarta colleagues. Brand-insecure. LinkedIn poster."
        )
    }
]

# Rate limit: 10,000 output TPM for claude-haiku-4-5-20251001
# Call 1 (genome): ~350 tokens, Call 2 (blueprint): ~1000 tokens → ~1350 tokens per agent
# Sleep 70s between agents → safely under limit
SLEEP_BETWEEN_AGENTS = 70


def clamp_ints(data: dict) -> dict:
    for field in [
        "openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism",
        "communication_style", "decision_making", "brand_relationship",
        "influence_susceptibility", "emotional_expression", "conflict_behavior",
        "identity_fusion", "chronesthesia_capacity", "tom_self_awareness",
        "tom_social_modeling", "executive_flexibility"
    ]:
        if field in data and data[field] is not None:
            data[field] = max(1, min(100, int(data[field])))
    return data


def call_tool(tool_def: dict, user_message: str, max_tokens: int = 1000, retries: int = 3) -> dict | None:
    """Single tool-forced Anthropic call. Returns tool input dict or None on failure."""
    for attempt in range(1, retries + 1):
        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=max_tokens,
                system=SYSTEM_PROMPT,
                tools=[tool_def],
                tool_choice={"type": "tool", "name": tool_def["name"]},
                messages=[{"role": "user", "content": user_message}]
            )
            block = next((b for b in response.content if b.type == "tool_use"), None)
            if block is None:
                raise ValueError("No tool_use block returned")
            print(f"      [stop={response.stop_reason} out_tokens={response.usage.output_tokens}]")
            return block.input

        except anthropic.RateLimitError as e:
            # Respect the retry-after header if available, otherwise default to 65s
            retry_after = 65
            try:
                retry_after = int(e.response.headers.get("retry-after", 65)) + 2
            except Exception:
                pass
            print(f"      ⚠ Rate limit hit. Sleeping {retry_after}s (retry-after header)...")
            time.sleep(retry_after)

        except anthropic.BadRequestError as e:
            print(f"      ✗ Bad request (non-retryable): {e}")
            return None

        except Exception as e:
            print(f"      ✗ Attempt {attempt}/{retries}: {e}")
            if attempt < retries:
                time.sleep(5)

    return None


def generate_agent(archetype: dict, index: int) -> dict | None:
    """Generate genome via 2 targeted tool calls. Returns merged dict or None."""
    seed = archetype["seed"]

    # --- Call 1: Personality genome + voice print ---
    print(f"    Call 1/2: personality + voice print...")
    genome_msg = (
        f"Agent profile: {seed}\n\n"
        "Assign personality scores and voice print. "
        "Every integer must be justified by this person's background."
    )
    genome = call_tool(GENOME_TOOL, genome_msg, max_tokens=500)
    if genome is None:
        return None

    if not isinstance(genome.get("voice_print"), dict):
        print(f"      ✗ voice_print missing from genome response")
        return None

    # --- Call 2: Life blueprint layers ---
    print(f"    Call 2/2: life blueprint layers...")
    blueprint_msg = (
        f"Agent profile: {seed}\n\n"
        f"Personality scores: "
        f"openness={genome.get('openness')}, conscientiousness={genome.get('conscientiousness')}, "
        f"extraversion={genome.get('extraversion')}, neuroticism={genome.get('neuroticism')}.\n\n"
        "Generate ALL 5 life layers. STRICT BREVITY RULES:\n"
        "- summary: 1 short sentence (max 15 words)\n"
        "- key_events: exactly 3 items, each max 8 words\n"
        "- psychological_impact: 1 short sentence (max 12 words)\n"
        "All 5 layers must fit in one response. Do not write long sentences."
    )
    blueprint = call_tool(BLUEPRINT_TOOL, blueprint_msg, max_tokens=1500)
    if blueprint is None:
        return None

    # Validate all layers present
    for layer in ["origin_layer", "formation_layer", "independence_layer", "maturity_layer", "legacy_layer"]:
        if not isinstance(blueprint.get(layer), dict):
            print(f"      ✗ '{layer}' missing from blueprint response")
            return None

    # Apply age drift before merging
    genome = apply_age_drift(clamp_ints(genome), archetype["age"])

    # Merge
    result = genome
    result.update(blueprint)
    return result


def insert_agent(data: dict, archetype: dict, demographic: str, region: str):
    payload = {
        "id":                    str(uuid.uuid4()),
        "created_at":            datetime.now(timezone.utc).isoformat(),
        "target_demographic":    demographic,
        "age":                   archetype["age"],
        "region":                region,
        "openness":              data["openness"],
        "conscientiousness":     data["conscientiousness"],
        "extraversion":          data["extraversion"],
        "agreeableness":         data["agreeableness"],
        "neuroticism":           data["neuroticism"],
        "communication_style":   data["communication_style"],
        "decision_making":       data["decision_making"],
        "brand_relationship":    data["brand_relationship"],
        "influence_susceptibility": data["influence_susceptibility"],
        "emotional_expression":  data["emotional_expression"],
        "conflict_behavior":     data["conflict_behavior"],
        "identity_fusion":       data["identity_fusion"],
        "chronesthesia_capacity": data["chronesthesia_capacity"],
        "tom_self_awareness":    data["tom_self_awareness"],
        "tom_social_modeling":   data["tom_social_modeling"],
        "executive_flexibility": data["executive_flexibility"],
        "origin_layer":          data["origin_layer"],
        "formation_layer":       data["formation_layer"],
        "independence_layer":    data["independence_layer"],
        "maturity_layer":        data["maturity_layer"],
        "legacy_layer":          data["legacy_layer"],
        "voice_print":           data["voice_print"],
    }
    supabase.table("agent_genomes").insert(payload).execute()


def main():
    demographic = "Medanese Upper Middle Class, 25-45"
    region = "Medan, North Sumatra, Indonesia"
    n = len(ARCHETYPES)

    print("\n═══ PANTHEON Genesis Protocol ═══")
    print(f"  Demographic : {demographic}")
    print(f"  Region      : {region}")
    print(f"  Agents      : {n}")
    print(f"  Model       : claude-haiku-4-5-20251001")
    print(f"  Strategy    : 2 tool calls/agent (genome + blueprint)")
    print(f"  Est. tokens : ~1550/agent (target ~$0.05/agent)")
    print(f"  Pacing      : {SLEEP_BETWEEN_AGENTS}s between agents (~8 min total)\n")

    success = 0
    for i, archetype in enumerate(ARCHETYPES, 1):
        print(f"[{i}/{n}] Age {archetype['age']} archetype...")

        if i > 1:
            print(f"  Sleeping {SLEEP_BETWEEN_AGENTS}s (rate-limit buffer)...")
            time.sleep(SLEEP_BETWEEN_AGENTS)

        data = generate_agent(archetype, i)

        if data is None:
            print(f"  ✗ Agent {i} FAILED — skipping\n")
            continue

        try:
            insert_agent(data, archetype, demographic, region)
            success += 1
            vp = data["voice_print"]
            print(f"  ✓ Stored in Supabase — all columns filled")
            print(f"    Genome  : O={data['openness']} C={data['conscientiousness']} "
                  f"E={data['extraversion']} A={data['agreeableness']} N={data['neuroticism']} | "
                  f"CommStyle={data['communication_style']} Dec={data['decision_making']} "
                  f"Brand={data['brand_relationship']} Influ={data['influence_susceptibility']} "
                  f"EmotExp={data['emotional_expression']} Conflict={data['conflict_behavior']}")
            print(f"    Voice   : {vp['vocabulary_level'][:90]}")
            print(f"    Triggers: {', '.join(vp['persuasion_triggers'])}")
        except Exception as e:
            print(f"  ✗ Supabase insert failed: {e}")

        print()

    print(f"═══ Genesis complete: {success}/{n} agents stored ═══")
    if success > 0:
        r = supabase.table("agent_genomes").select("id", count="exact").execute()
        print(f"    Total agents in DB: {r.count}")


if __name__ == "__main__":
    main()
