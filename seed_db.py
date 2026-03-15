import os
import json
import random
import time
from dotenv import load_dotenv
from supabase import create_client, Client
import anthropic

from genome_culture import (
    GENESIS_SYSTEM_PROMPT,
    generate_base_genome,
    apply_age_drift,
    generate_cultural_profile,
    apply_cultural_modifiers,
)

load_dotenv('pantheon.env', override=True)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")


def build_and_push_agent(
    supabase: Client,
    client: anthropic.Anthropic,
    agent_index: int,
    demographic: str,
    age: int,
    region: str,
    retries: int = 3,
):
    # ── Step 1: Generate base genome ─────────────────────────────────────────
    base_genome = generate_base_genome()

    # ── Step 2: Apply age drift ───────────────────────────────────────────────
    base_genome = apply_age_drift(base_genome, age)

    # ── Step 3: Generate cultural/religious profile ───────────────────────────
    profile = generate_cultural_profile(region, age)

    # ── Step 4: Apply cultural modifiers to genome ────────────────────────────
    genome = apply_cultural_modifiers(base_genome, profile)

    # ── Step 4: Build user prompt ─────────────────────────────────────────────
    user_prompt = (
        f"Generate a hyper-realistic life blueprint for a {age}-year-old {demographic} from {region}.\n\n"
        f"GENOME SCORES (1–100 scale — your narrative MUST justify these exact values):\n"
        f"  openness={genome['openness']}, conscientiousness={genome['conscientiousness']}, "
        f"extraversion={genome['extraversion']}, agreeableness={genome['agreeableness']}, "
        f"neuroticism={genome['neuroticism']}, communication_style={genome['communication_style']}, "
        f"decision_making={genome['decision_making']}, brand_relationship={genome['brand_relationship']}, "
        f"influence_susceptibility={genome['influence_susceptibility']}, "
        f"emotional_expression={genome['emotional_expression']}, "
        f"conflict_behavior={genome['conflict_behavior']}\n"
        f"  literacy_and_articulation={genome['literacy_and_articulation']}, "
        f"socioeconomic_friction={genome['socioeconomic_friction']}\n\n"
        f"{profile['cultural_context_for_prompt']}\n\n"
        f"Each life layer's key events must psychologically justify why this person has exactly these scores. "
        f"Ground this agent in authentic North American urban millennial experience — "
        f"student debt, gig economy, social media identity, housing costs, political polarization, "
        f"and the ongoing negotiation between inherited values and modern urban culture.\n"
        f"Output ONLY valid JSON."
    )

    for attempt in range(1, retries + 1):
        try:
            print(f"  ⏳ [Agent {agent_index}] Attempt {attempt} | {profile['ethnicity']} | "
                  f"{profile['religion_of_origin']} → {profile['current_religion']} | "
                  f"religiosity={profile['religiosity']}")

            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=4000,
                system=GENESIS_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}]
            )
            raw_text = response.content[0].text
            # Strip any accidental markdown fences
            if raw_text.startswith("```json"): raw_text = raw_text[7:]
            if raw_text.startswith("```"):     raw_text = raw_text[3:]
            if raw_text.endswith("```"):       raw_text = raw_text[:-3]
            raw_text = raw_text.strip()

            blueprint_data = json.loads(raw_text)

            # ── Merge mutation logs: cultural events first, then Claude's life events ──
            combined_mutation_log = (
                profile["cultural_mutation_events"]
                + blueprint_data.pop("genome_mutation_log", [])
            )

            # ── Build final payload ───────────────────────────────────────────
            import uuid
            import datetime
            payload = {
                # Metadata
                "id":                 str(uuid.uuid4()),
                "created_at":         datetime.datetime.utcnow().isoformat(),
                "target_demographic": demographic,
                "age":                age,
                "region":             region,
                # Cultural/religious columns
                "ethnicity":          profile["ethnicity"],
                "cultural_background":profile["ethnicity"],               # Legacy
                "cultural_primary":   profile["cultural_primary"],
                "cultural_secondary": profile["cultural_secondary"],
                "religion_of_origin": profile["religion_of_origin"],
                "current_religion":   profile["current_religion"],
                "religion":           profile["current_religion"],            # Legacy
                "religiosity":        profile["religiosity"],
                "partner_culture":    profile["partner_culture"],
                "partner_religion":   profile["partner_religion"],
                # Integer genome (with cultural modifiers applied)
                **genome,
                # Cognitive architecture columns
                "identity_fusion":         genome["identity_fusion"],
                "chronesthesia_capacity":  genome["chronesthesia_capacity"],
                "tom_self_awareness":      genome["tom_self_awareness"],
                "tom_social_modeling":     genome["tom_social_modeling"],
                "executive_flexibility":   genome["executive_flexibility"],
                # Claude-generated JSONB life layers + voice_print
                **blueprint_data,
                # Combined mutation log
                "genome_mutation_log": combined_mutation_log,
            }

            supabase.table("agent_genomes").insert(payload).execute()
            print(f"  ✅ [Agent {agent_index}] Stored — "
                  f"{'intercultural partner' if profile['partner_culture'] else 'single-culture'} | "
                  f"conversion: {profile['conversion_type']}")
            return True

        except json.JSONDecodeError as e:
            print(f"  ⚠️  [Agent {agent_index}] JSON parse error: {e}. Retrying...")
            time.sleep(2)
        except anthropic.RateLimitError:
            wait = 30
            print(f"  ⚠️  [Agent {agent_index}] Rate limited. Waiting {wait}s...")
            time.sleep(wait)
        except anthropic.APIStatusError as e:
            if e.status_code == 529:
                wait = 15 * attempt
                print(f"  ⚠️  [Agent {agent_index}] Anthropic overloaded (529). Waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"  ❌ [Agent {agent_index}] API Error {e.status_code}: {e}")
                return False
        except Exception as e:
            print(f"  ❌ [Agent {agent_index}] Failed: {e}")
            return False

    print(f"  ❌ [Agent {agent_index}] Failed after {retries} retries.")
    return False


def main():
    if not SUPABASE_URL or not ANTHROPIC_API_KEY:
        print("❌ Missing SUPABASE_URL or ANTHROPIC_API_KEY in pantheon.env!")
        return

    supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    claude_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    existing = supabase_client.table("agent_genomes").select("id", count="exact").execute()
    print(f"📊 Current agents in DB: {existing.count}")

    target_demographic = "Urban Millennial"
    region = "North America"
    total_agents = 20
    delay_between = 1

    print(f"\n🚀 Starting Genesis Protocol: Seeding {total_agents} agents for '{target_demographic}'...")
    print(f"   Cultural engine: ethnicity + religion + conversion + intercultural marriage\n")

    success = 0
    for i in range(1, total_agents + 1):
        age = random.randint(28, 43)
        result = build_and_push_agent(supabase_client, claude_client, i, target_demographic, age, region)
        if result:
            success += 1
        time.sleep(delay_between)

    print(f"\n🎯 Genesis seeding complete! {success}/{total_agents} agents stored successfully.")


if __name__ == "__main__":
    main()
