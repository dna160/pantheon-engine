import os
import json
import random
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any

_MUTABLE_TRAITS = [
    "openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism",
    "communication_style", "decision_making", "brand_relationship",
    "influence_susceptibility", "emotional_expression", "conflict_behavior",
    "literacy_and_articulation", "socioeconomic_friction",
    "identity_fusion", "chronesthesia_capacity", "tom_self_awareness",
    "tom_social_modeling", "executive_flexibility",
    "religiosity",
]

_GENOME_TOOL = {
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
            "literacy_and_articulation": {
                "type": "integer",
                "description": "1=barely literate/inarticulate with very simple vocabulary, 100=eloquent and highly educated. Dictates vocabulary complexity, sentence structure, and speaking confidence."
            },
            "socioeconomic_friction": {
                "type": "integer",
                "description": "1=minimal barriers/comfortable life trajectory, 100=severe systemic barriers, crushing debt, career stagnation, or chronic financial precarity. Shapes pessimism, risk-aversion, and distrust of financial products."
            },
            "identity_fusion": {
                "type": "integer",
                "description": "1=pure individualist (evaluates everything on personal merit), 100=visceral group oneness (will sacrifice personal utility to protect family/clan/community honor). Drives mianzi, marga, guanxi, familismo behaviors."
            },
            "chronesthesia_capacity": {
                "type": "integer",
                "description": "1=present-only thinker (reactive, no future simulation), 100=vivid mental time traveler (constantly projects decisions 5-10 years forward, queries past memories to validate choices)."
            },
            "tom_self_awareness": {
                "type": "integer",
                "description": "1=blind to own emotional states and biases, 100=deep self-reflection (accurately identifies own motivations, recognizes own cognitive distortions)."
            },
            "tom_social_modeling": {
                "type": "integer",
                "description": "1=oblivious to how others perceive them, 100=reads rooms perfectly (accurately models what others think of them, predicts social reactions)."
            },
            "executive_flexibility": {
                "type": "integer",
                "description": "1=base traits leak into all contexts regardless of social norms, 100=can fully override impulses in context-appropriate situations (the professional who is privately anxious but appears calm)."
            },
            "current_religion": {
                "type": "string",
                "description": "Specific religious practice and denomination/sect, defining behavior/diet/finances (e.g., 'Conservative Sunni Muslim - halal strict', 'Devout Catholic - family-centric', 'Nominally Buddhist', 'Pentecostal - tithing')."
            },
            "religiosity": {
                "type": "integer",
                "description": "1=completely nominal/secular (religion has zero practical effect on daily behavior), 100=devout and observant (religion dictates diet, dress, finances, social circle, and daily schedule)."
            },
            "ethnicity": {
                "type": "string",
                "description": "Short ethnicity label rooted in the assigned city/region (e.g., 'Javanese', 'Chinese-Indonesian', 'Batak Toba', 'Minangkabau', 'Betawi', 'Sundanese', 'Bugis', 'Malay'). Must be authentic to the ASSIGNED CITY."
            },
            "cultural_primary": {
                "type": "string",
                "description": "Dominant cultural identity that shapes this person's worldview, family norms, and shame mechanics (e.g., 'Javanese priyayi — hierarchical, indirect, refinement-obsessed', 'Batak Toba — clan honor, loud negotiation, adat-rooted', 'Chinese-Indonesian — mianzi, guanxi, filial piety')."
            },
            "cultural_secondary": {
                "type": "string",
                "description": "Secondary cultural layer from migration, education, or partner influence (e.g., 'Westernized by Singapore MBA', 'Javanese mother, Batak father — identity negotiation ongoing', 'None — monocultural'). Use 'None' if not applicable."
            },
            "partner_culture": {
                "type": "string",
                "description": "Partner or spouse's cultural background and its influence on purchasing decisions (e.g., 'Sundanese wife — consensus-driven purchasing', 'No partner', 'Mixed-culture marriage — dual approval required for big purchases')."
            },
            "voice_print": {
                "type": "object",
                "properties": {
                    "vocabulary_level":    {"type": "string"},
                    "filler_words":        {"type": "array", "items": {"type": "string"}},
                    "persuasion_triggers": {"type": "array", "items": {"type": "string"}},
                    "conflict_style":      {"type": "string"}
                },
                "required": ["vocabulary_level", "filler_words", "persuasion_triggers", "conflict_style"],
                "additionalProperties": False
            }
        },
        "required": [
            "openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism",
            "communication_style", "decision_making", "brand_relationship",
            "influence_susceptibility", "emotional_expression", "conflict_behavior",
            "literacy_and_articulation", "socioeconomic_friction",
            "identity_fusion", "chronesthesia_capacity", "tom_self_awareness",
            "tom_social_modeling", "executive_flexibility",
            "current_religion", "religiosity", "ethnicity",
            "cultural_primary", "cultural_secondary", "partner_culture", "voice_print"
        ],
        "additionalProperties": False
    }
}

_LAYER_DEF = {
    "type": "object",
    "properties": {
        "summary":              {"type": "string", "description": "MAX 100 chars. 1 sentence."},
        "key_events":           {"type": "array", "items": {"type": "string"}, "description": "Exactly 3 items, each MAX 60 chars"},
        "psychological_impact": {"type": "string", "description": "MAX 80 chars. 1 sentence."}
    },
    "required": ["summary", "key_events", "psychological_impact"],
    "additionalProperties": False
}

_BLUEPRINT_TOOL = {
    "name": "submit_blueprint",
    "description": "Submit all 5 life stage layers. ALL layers required.",
    "input_schema": {
        "type": "object",
        "properties": {
            "origin_layer":       _LAYER_DEF,
            "formation_layer":    _LAYER_DEF,
            "independence_layer": _LAYER_DEF,
            "maturity_layer":     _LAYER_DEF,
            "legacy_layer":       _LAYER_DEF,
        },
        "required": ["origin_layer", "formation_layer", "independence_layer", "maturity_layer", "legacy_layer"],
        "additionalProperties": False
    }
}

_MUTATION_TOOL = {
    "name": "submit_mutation_log",
    "description": "Submit the Nature vs. Nurture mutation log.",
    "input_schema": {
        "type": "object",
        "properties": {
            "genome_mutation_log": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "life_stage": {"type": "string", "enum": ["Origin", "Formation", "Independence", "Maturity", "Legacy"]},
                        "event_description": {"type": "string"},
                        "trait_modifiers": {"type": "object", "additionalProperties": {"type": "integer"}}
                    },
                    "required": ["life_stage", "event_description", "trait_modifiers"]
                }
            }
        },
        "required": ["genome_mutation_log"]
    }
}

_INDONESIAN_CITIES = [
    "Jakarta", "Surabaya", "Bandung", "Medan", "Makassar", "Semarang", "Yogyakarta",
    "Palembang", "Bali (Denpasar)", "Balikpapan", "Malang", "Manado", "Pekanbaru",
    "Pontianak", "Banjarmasin"
]

# Keyword → canonical city name. Checked against lowercased demographic string.
_CITY_KEYWORDS: dict[str, str] = {
    "jakarta": "Jakarta",
    "jabodetabek": "Jakarta",
    "tangerang": "Jakarta",
    "bekasi": "Jakarta",
    "depok": "Jakarta",
    "bogor": "Jakarta",
    "surabaya": "Surabaya",
    "bandung": "Bandung",
    "medan": "Medan",
    "makassar": "Makassar",
    "ujung pandang": "Makassar",
    "semarang": "Semarang",
    "yogyakarta": "Yogyakarta",
    "yogya": "Yogyakarta",
    "jogja": "Yogyakarta",
    "palembang": "Palembang",
    "bali": "Bali (Denpasar)",
    "denpasar": "Bali (Denpasar)",
    "balikpapan": "Balikpapan",
    "malang": "Malang",
    "manado": "Manado",
    "pekanbaru": "Pekanbaru",
    "pontianak": "Pontianak",
    "banjarmasin": "Banjarmasin",
}

# Each template is tagged with the ethnicities it represents so we can
# weight selection toward templates that match the demographic text.
_SEED_TEMPLATES: list[dict] = [
    {
        "tags": ["chinese", "peranakan", "tionghoa"],
        "template": "Chinese-Indonesian {age}yo, third-generation trading family in {city}, conservative, status-conscious, clan association active, luxury-car aspirations."
    },
    {
        "tags": ["batak", "toba", "christian"],
        "template": "Batak Toba {age}yo professional (lawyer/doctor/engineer) now based in {city}, feminist but adat-rooted, heavy Instagram user, premium-mall shopper, skeptical of ads."
    },
    {
        "tags": ["javanese", "java", "jawa"],
        "template": "Javanese {age}yo entrepreneur or startup founder based in {city}, GrabFood/TikTok/Tokopedia native, frugal personally but aggressive in business, peer-recommendation-driven."
    },
    {
        "tags": ["minangkabau", "minang", "padang", "west sumatera"],
        "template": "Minangkabau {age}yo female professional in {city}, evidence-driven, remittance sender, slow decision-maker with extreme conviction, anti-influencer, clinic or consultancy owner."
    },
    {
        "tags": ["batak", "karo", "dayak", "kalimantan"],
        "template": "Batak Karo / Dayak {age}yo regional manager or sales director in {city}, rose from field ops, sends kids to international school, peer-influenced, LinkedIn poster, brand-insecure."
    },
    {
        "tags": ["chinese", "peranakan", "tionghoa"],
        "template": "Chinese-Peranakan {age}yo in {city}, property investor or café owner, bilingual Chinese-dialect/Bahasa, mianzi-driven, early adopter of premium lifestyle brands."
    },
    {
        "tags": ["sundanese", "sunda", "javanese", "java", "jawa"],
        "template": "Sundanese/Javanese {age}yo salaried professional in {city} (banking/FMCG/government), quietly status-conscious, Shopee/Tokopedia power-user, brand-loyal to established names."
    },
    {
        "tags": ["bugis", "sulawesi", "makassar"],
        "template": "Bugis {age}yo entrepreneur in {city}, maritime-trade heritage, tight community network, cash-first, distrustful of fintech debt products, drives hard bargains."
    },
    {
        "tags": ["acehnese", "aceh", "malay", "melayu"],
        "template": "Acehnese / Malay {age}yo in {city}, religiously observant, halal-compliant purchasing, rejects riba-adjacent products, strong family decision-making unit."
    },
    {
        "tags": ["urban", "millennial", "mixed"],
        "template": "Urban millennial {age}yo from {city}, mixed ethnicity, college-educated, remote-worker, high digital literacy, rents not owns, aspirational but cash-constrained."
    },
    {
        "tags": ["betawi", "jakarta", "jabodetabek"],
        "template": "Betawi {age}yo native of {city}, middle-class salaried worker, socially conservative, mosque-active, prefers brand names he recognizes from TV, resists aggressive sales tactics."
    },
    {
        "tags": ["chinese", "tionghoa", "jakarta", "surabaya", "bandung"],
        "template": "Chinese-Indonesian {age}yo second-generation business owner in {city}, secular Confucianist background, pragmatic buyer, distrusts government-linked products, relationship-driven."
    },
]


def _extract_city(demographic: str) -> str | None:
    """Return canonical city if demographic explicitly mentions one, else None."""
    lower = demographic.lower()
    for keyword, city in _CITY_KEYWORDS.items():
        if keyword in lower:
            return city
    return None


def _pick_template(demographic: str) -> str:
    """Return a template whose tags best match the demographic text, with random tiebreaking."""
    lower = demographic.lower()
    scored: list[tuple[int, dict]] = []
    for entry in _SEED_TEMPLATES:
        score = sum(1 for tag in entry["tags"] if tag in lower)
        scored.append((score, entry))
    max_score = max(s for s, _ in scored)
    # If any tags matched, pick from the best-matching set; else use all templates.
    candidates = [e for s, e in scored if s == max_score and (max_score > 0 or True)]
    chosen = random.choice(candidates)
    return chosen["template"]

_GENESIS_SYSTEM_BASE = (
    "You are PANTHEON Genesis Builder: generating psychologically coherent Indonesian consumer profiles.\n"
    "Your role is to create realistic synthetic humans for market research simulations."
    # ... (rest of the base system prompt)
)

def _build_genesis_system(city: str, demographic: str) -> str:
    return (
        f"{_GENESIS_SYSTEM_BASE}\n\n"
        f"ASSIGNED CITY FOR THIS AGENT: {city}\n"
        f"TARGET DEMOGRAPHIC: {demographic}\n"
        f"You must produce a profile that is authentically rooted in {city}."
    )

def _clamp_ints(data: dict) -> dict:
    for field in _MUTABLE_TRAITS:
        if field in data and data[field] is not None:
            data[field] = max(1, min(100, int(data[field])))
    return data

def _apply_mutations(base_genome: dict, mutation_log: list[dict]) -> dict:
    final = dict(base_genome)
    for event in mutation_log:
        modifiers = event.get("trait_modifiers") or {}
        for trait, delta in modifiers.items():
            if trait not in _MUTABLE_TRAITS:
                continue
            current = final.get(trait, 50)
            final[trait] = max(1, min(100, int(current) + int(delta)))
    return final

def _genesis_call_tool(anthropic_client, tool_def: dict, user_message: str, system_prompt: str, max_tokens: int = 1000, retries: int = 3) -> dict | None:
    import anthropic as _anthropic
    for attempt in range(1, retries + 1):
        try:
            response = anthropic_client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=max_tokens,
                system=system_prompt,
                tools=[tool_def],
                tool_choice={"type": "tool", "name": tool_def["name"]},
                messages=[{"role": "user", "content": user_message}]
            )
            block = next((b for b in response.content if b.type == "tool_use"), None)
            if block is None: raise ValueError("No tool_use block returned")
            return block.input
        except _anthropic.RateLimitError as e:
            wait = 65
            try: wait = int(e.response.headers.get("retry-after", 65)) + 2
            except: pass
            time.sleep(wait)
        except Exception:
            if attempt < retries: time.sleep(5)
    return None

def _generate_one_agent(anthropic_client, age: int, seed: str, city: str, demographic: str) -> dict | None:
    system_prompt = _build_genesis_system(city, demographic)
    genome_msg = f"CITY FOR THIS AGENT: {city}\nAgent profile: {seed}\n\nSTEP 1 — Base Nature..."
    base_genome = _genesis_call_tool(anthropic_client, _GENOME_TOOL, genome_msg, system_prompt=system_prompt, max_tokens=500)
    if base_genome is None: return None
    base_genome = _clamp_ints(base_genome)

    mutation_msg = f"CITY FOR THIS AGENT: {city}\nAgent profile: {seed}\nBase Genome: {base_genome}\n\nSTEP 2 & 3 — Variable Life Path..."
    mutation_result = _genesis_call_tool(anthropic_client, _MUTATION_TOOL, mutation_msg, system_prompt=system_prompt, max_tokens=1200)
    mutation_log = mutation_result.get("genome_mutation_log") or [] if mutation_result else []
    
    final_genome = _apply_mutations(base_genome, mutation_log)
    
    blueprint_msg = f"CITY FOR THIS AGENT: {city}\nAgent profile: {seed}\nFinal Genome: {final_genome}\n\nGenerate ALL 5 life layers..."
    blueprint = _genesis_call_tool(anthropic_client, _BLUEPRINT_TOOL, blueprint_msg, system_prompt=system_prompt, max_tokens=1500)
    if blueprint is None: return None
    
    result = dict(final_genome)
    result.update(blueprint)
    result["genome_mutation_log"] = mutation_log
    return result

def dynamic_seed_agents(demographic: str, count: int, sb, anthropic_client) -> list[dict]:
    age_match = re.search(r"(\d+)[^\d]+(\d+)", demographic)
    age_min, age_max = (int(age_match.group(1)), int(age_match.group(2))) if age_match else (25, 45)

    # Lock city to whatever is mentioned in the demographic; fall back to random only if none found.
    pinned_city = _extract_city(demographic)

    created = []
    for i in range(count):
        city = pinned_city if pinned_city else random.choice(_INDONESIAN_CITIES)
        age = random.randint(age_min, age_max)
        template = _pick_template(demographic)
        seed = template.format(age=age, city=city)
        data = _generate_one_agent(anthropic_client, age, seed, city=city, demographic=demographic)
        if data is None: continue
        payload = {
            "id": str(uuid.uuid4()),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "target_demographic": demographic,
            "age": age,
            "region": f"{city}, Indonesia",
            **{k: data.get(k, 50) for k in _MUTABLE_TRAITS},
            "ethnicity": data.get("ethnicity", "Unspecified"),
            "current_religion": data.get("current_religion", "Unspecified"),
            "cultural_primary": data.get("cultural_primary", ""),
            "cultural_secondary": data.get("cultural_secondary", ""),
            "partner_culture": data.get("partner_culture", ""),
            "genome_mutation_log": data.get("genome_mutation_log", []),
            "origin_layer": data.get("origin_layer", ""),
            "formation_layer": data.get("formation_layer", ""),
            "independence_layer": data.get("independence_layer", ""),
            "maturity_layer": data.get("maturity_layer", ""),
            "legacy_layer": data.get("legacy_layer", ""),
            "voice_print": data.get("voice_print", ""),
        }
        sb.table("agent_genomes").insert(payload).execute()
        created.append(payload)
    return created
