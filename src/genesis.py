import os
import json
import random
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any

# ─────────────────────────────────────────────────────────────────────────────
# TRAIT REGISTRY
# All numeric traits that participate in mutation clamping.
# ─────────────────────────────────────────────────────────────────────────────
_MUTABLE_TRAITS = [
    # Big Five
    "openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism",
    # Behavioral
    "communication_style", "decision_making", "brand_relationship",
    "influence_susceptibility", "emotional_expression", "conflict_behavior",
    # Socioeconomic
    "literacy_and_articulation", "socioeconomic_friction",
    # PANTHEON Framework — 5 Cognitive Dimensions (from whitepaper)
    "cumulative_cultural_capacity",  # Ratchet-effect cultural integration
    "identity_fusion",               # Hyper-cooperation / self→group dissolution
    "chronesthesia_capacity",        # Mental time travel / episodic foresight
    "tom_self_awareness",            # Theory of Mind: self-modeling
    "tom_social_modeling",           # Theory of Mind: other-modeling
    "executive_flexibility",         # Top-down inhibitory control
    # Religion
    "religiosity",
]

# ─────────────────────────────────────────────────────────────────────────────
# GENOME TOOL
# Forces the LLM to produce a grounded narrative BEFORE scoring, ensuring
# trait scores derive from the person rather than being arbitrary numbers.
# ─────────────────────────────────────────────────────────────────────────────
_GENOME_TOOL = {
    "name": "submit_genome",
    "description": (
        "Submit the complete personality genome. CRITICAL: write persona_narrative FIRST "
        "to ground all integer scores in a coherent individual. ALL fields required."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            # ── Grounding narrative ───────────────────────────────────────────
            "persona_narrative": {
                "type": "string",
                "description": (
                    "3-4 sentences describing this SPECIFIC individual — their defining contradiction, "
                    "the wound that shaped them, the mask they wear professionally, and the one thing "
                    "that motivates them beyond money. This narrative MUST justify every score below. "
                    "Write this before scoring anything else."
                )
            },
            # ── Big Five ─────────────────────────────────────────────────────
            "openness":          {"type": "integer", "description": "1=dogmatically closed, 100=radically experimental. Reflects CCC score — high CCC agents trend high openness unless religion/tradition counterweights."},
            "conscientiousness": {"type": "integer", "description": "1=chaotic/impulsive, 100=methodical/disciplined. High chronesthesia + low conscientiousness = visionary chaos agent."},
            "extraversion":      {"type": "integer", "description": "1=deep introvert, 100=social dynamo. Javanese high-exec-flexibility agents often display LOWER extraversion publicly than privately."},
            "agreeableness":     {"type": "integer", "description": "1=adversarial/suspicious, 100=deferential/cooperative. High identity_fusion + low agreeableness = dangerous tribalist (warm to in-group, hostile to out-group)."},
            "neuroticism":       {"type": "integer", "description": "1=psychologically stable, 100=chronically anxious. Low exec_flexibility + high neuroticism = emotional flooding into all contexts."},
            # ── Behavioral ───────────────────────────────────────────────────
            "communication_style":      {"type": "integer", "description": "1=highly indirect/coded speech, 100=blunt/explicit. Javanese cultural mask = low; Batak adat = high."},
            "decision_making":          {"type": "integer", "description": "1=gut-driven/intuitive, 100=data-driven/analytical. High tom_self_awareness usually raises this."},
            "brand_relationship":       {"type": "integer", "description": "1=purely price-driven/commodity thinker, 100=deeply brand-loyal/identity-linked. High mianzi/marga identity_fusion raises this."},
            "influence_susceptibility": {"type": "integer", "description": "1=impervious to social proof, 100=highly susceptible to peer/influencer pressure. High CCC + low tom_self_awareness = very susceptible."},
            "emotional_expression":     {"type": "integer", "description": "1=stoic/masked, 100=openly expressive. Low exec_flexibility = high leakage of true emotional state."},
            "conflict_behavior":        {"type": "integer", "description": "1=conflict-avoidant at all costs (rukun), 100=directly confrontational. Batak: high. Javanese: low displayed, privately different."},
            # ── Socioeconomic ─────────────────────────────────────────────────
            "literacy_and_articulation": {
                "type": "integer",
                "description": (
                    "1=barely literate, simple vocabulary, inarticulate under pressure. "
                    "100=eloquent, highly educated, precise under pressure. "
                    "Dictates vocabulary complexity, sentence structure, confidence in formal settings."
                )
            },
            "socioeconomic_friction": {
                "type": "integer",
                "description": (
                    "1=minimal barriers, comfortable trajectory, inherited safety net. "
                    "100=severe systemic barriers: crushing debt, career stagnation, generational poverty, "
                    "chronic financial precarity. Shapes pessimism, risk-aversion, distrust of financial products."
                )
            },
            # ── PANTHEON Framework: 5 Cognitive Dimensions ────────────────────
            "cumulative_cultural_capacity": {
                "type": "integer",
                "description": (
                    "PANTHEON Dimension 1 — The ratchet-effect cultural integration score. "
                    "How deeply is this person embedded in collective knowledge transmission? "
                    "15-30: Individualistic; innovations disappear; tradition-resistant. "
                    "31-55: Replicates others accurately; tradition-follower but not propagator. "
                    "56-78: Actively teaches and transmits; success-biased conformist; upholds group norms. "
                    "79-100: Deep networked conformity; treats community knowledge as sacred infrastructure; "
                    "drives open-ended recombination across generations."
                )
            },
            "identity_fusion": {
                "type": "integer",
                "description": (
                    "PANTHEON Dimension 4 — Hyper-cooperation: psychological dissolution of self into group. "
                    "10-25: Strictly self-interested; defects in anonymous economic games; kin-only altruism. "
                    "26-52: Moody conditional cooperator; fairness-sensitive; transactional prosociality. "
                    "53-76: Institutional prosociality; punishes free-riders; trusts collective enforcement. "
                    "77-100: Complete fusion — will sacrifice physical safety for non-kin group or abstract "
                    "sacred values. Drives sectarian loyalty, martyrdom, extreme brand tribalism, marga honor."
                )
            },
            "chronesthesia_capacity": {
                "type": "integer",
                "description": (
                    "PANTHEON Dimension 3 — Episodic foresight: autonoetic mental time travel. "
                    "10-28: Present-bound; no future simulation beyond immediate consequences; reactive. "
                    "29-52: Domain-specific episodic recall; limited future prep; not tied to narrative self. "
                    "53-78: Vivid episodic reconstruction; strategic long-range planning; uses past to simulate future. "
                    "79-100: Intergenerational foresight; designs for unborn generations; sacrifices present utility "
                    "for abstract future states (saves for children's education 20 years out)."
                )
            },
            "tom_self_awareness": {
                "type": "integer",
                "description": (
                    "PANTHEON Dimension 2a — Theory of Mind: self-modeling accuracy. "
                    "10-30: Blind to own biases; acts on impulse; cannot narrate own emotional drivers. "
                    "31-55: Labels surface emotions; limited introspective depth; post-hoc rationalization. "
                    "56-78: Identifies own cognitive distortions; tracks own patterns; psychological self-narration. "
                    "79-100: Deep metacognition; audits own belief system in real-time; detects own manipulation."
                )
            },
            "tom_social_modeling": {
                "type": "integer",
                "description": (
                    "PANTHEON Dimension 2b — Theory of Mind: other-modeling accuracy. "
                    "10-25: Uses others' perspectives for selfish/competitive gain only (Machiavellian). "
                    "26-50: First-order prosocial empathy; basic cooperation; passes false-belief tasks. "
                    "51-78: Second-order nested reasoning (what A thinks B thinks); drives complex negotiation. "
                    "79-100: Hyper-reflexive; models institutional minds; reads group dynamics in real-time; "
                    "navigates ambiguous multi-agent environments effortlessly."
                )
            },
            "executive_flexibility": {
                "type": "integer",
                "description": (
                    "PANTHEON Dimension 5 — Inhibitory control: top-down cortical override of biological impulses. "
                    "10-28: Base traits leak through all contexts regardless of social setting; emotionally reactive. "
                    "29-52: Basic rule learning; inhibition collapses under emotional load or high-stakes pressure. "
                    "53-78: Robust inhibitory control; professional mask holds under normal stress; dual-task capable. "
                    "79-100: Hyper-flexible abstract control; completely decouples behavior from overwhelming emotion; "
                    "performs at peak under maximum psychological pressure (surgeon operating on family member)."
                )
            },
            # ── Religion ──────────────────────────────────────────────────────
            "current_religion": {
                "type": "string",
                "description": (
                    "Specific religious practice with sect and behavioral impact. "
                    "E.g., 'Conservative Sunni Muslim — halal-strict, avoids riba, mosque-active', "
                    "'Nominal Sunni Muslim — mosque only on Eid, no food restrictions', "
                    "'Batak Protestant — church-weekly, tithing, family prayer mandatory', "
                    "'Nominally Buddhist — ancestral rituals only', 'Secular — no practice'."
                )
            },
            "religiosity": {
                "type": "integer",
                "description": (
                    "1=completely secular (religion has zero effect on daily behavior). "
                    "100=fully observant (religion dictates diet, dress, finance, schedule, social circle). "
                    "Indonesia calibration: 15-35=abangan/nominal, 36-60=practicing, 61-82=santri/devout, 83-100=activist."
                )
            },
            # ── Cultural Identity ──────────────────────────────────────────────
            "ethnicity": {
                "type": "string",
                "description": (
                    "Concise ethnicity label authentic to the ASSIGNED CITY. "
                    "E.g., 'Javanese', 'Betawi', 'Chinese-Indonesian (Tionghoa)', 'Batak Toba', "
                    "'Minangkabau', 'Sundanese', 'Bugis', 'Malay', 'Dayak', 'Manado Minahasa'."
                )
            },
            "cultural_primary": {
                "type": "string",
                "description": (
                    "Dominant cultural operating system: the norms, shame mechanics, hierarchy rules, "
                    "and family expectations that shape this person's default worldview. "
                    "E.g., 'Javanese priyayi — indirect speech, refinement obsession, hierarchical deference', "
                    "'Batak Toba — clan honor (marga), loud negotiation, adat-rooted obligations', "
                    "'Chinese-Indonesian — mianzi, guanxi networks, filial piety, face-preservation'."
                )
            },
            "cultural_secondary": {
                "type": "string",
                "description": (
                    "Secondary cultural layer acquired through migration, education, marriage, or diaspora. "
                    "E.g., 'Westernized by 3-year Singapore MBA', 'Javanese mother / Batak father — identity negotiation', "
                    "'Pesantren background overlaid on coastal trading culture', 'None — monocultural'."
                )
            },
            "partner_culture": {
                "type": "string",
                "description": (
                    "Partner/spouse's cultural background and its influence on purchasing and decision dynamics. "
                    "E.g., 'Sundanese wife — consensus purchasing, defers to extended family on big decisions', "
                    "'Chinese-Indonesian husband — dual-income, investment-oriented, brand-conscious', "
                    "'Mixed-culture marriage — dual approval required for purchases over 5M IDR', "
                    "'No partner — fully autonomous decision-maker'."
                )
            },
            # ── Voice Print ──────────────────────────────────────────────────
            "voice_print": {
                "type": "object",
                "description": "How this person actually speaks — must be consistent with literacy_and_articulation score and cultural background.",
                "properties": {
                    "vocabulary_level": {
                        "type": "string",
                        "description": "E.g., 'Formal Bahasa Indonesia mixed with English business terms', 'Casual Javanese-inflected Bahasa with minimal English', 'Highly educated formal Indonesian with academic register'"
                    },
                    "filler_words": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "3-5 actual filler words/phrases in Indonesian (e.g., ['ya', 'kan', 'gitu loh', 'pokoknya'])"
                    },
                    "persuasion_triggers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "3-5 specific triggers that move this person (e.g., ['social proof from peers in same SES bracket', 'family safety framing', 'scarcity with genuine time pressure'])"
                    },
                    "conflict_style": {
                        "type": "string",
                        "description": "How they actually handle disagreement (e.g., 'Goes silent and withdraws, then vents to spouse', 'Escalates rapidly but de-escalates equally fast', 'Uses humor to deflect, revisits issue days later')"
                    }
                },
                "required": ["vocabulary_level", "filler_words", "persuasion_triggers", "conflict_style"],
                "additionalProperties": False
            }
        },
        "required": [
            "persona_narrative",
            "openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism",
            "communication_style", "decision_making", "brand_relationship",
            "influence_susceptibility", "emotional_expression", "conflict_behavior",
            "literacy_and_articulation", "socioeconomic_friction",
            "cumulative_cultural_capacity", "identity_fusion", "chronesthesia_capacity",
            "tom_self_awareness", "tom_social_modeling", "executive_flexibility",
            "current_religion", "religiosity",
            "ethnicity", "cultural_primary", "cultural_secondary", "partner_culture",
            "voice_print"
        ],
        "additionalProperties": False
    }
}

# ─────────────────────────────────────────────────────────────────────────────
# BLUEPRINT TOOL
# Life stage layers — each must name which cognitive dimensions were shaped.
# ─────────────────────────────────────────────────────────────────────────────
_LAYER_DEF = {
    "type": "object",
    "properties": {
        "summary":              {"type": "string", "description": "MAX 120 chars. 1 sentence capturing the defining arc of this life stage."},
        "key_events":           {"type": "array", "items": {"type": "string"}, "description": "Exactly 3 specific events (not generic milestones). Each MAX 80 chars. Name the cognitive dimension each event shaped."},
        "psychological_impact": {"type": "string", "description": "MAX 100 chars. The lasting psychological residue — the wound, the adaptation, or the conviction that persists into adulthood."}
    },
    "required": ["summary", "key_events", "psychological_impact"],
    "additionalProperties": False
}

_BLUEPRINT_TOOL = {
    "name": "submit_blueprint",
    "description": (
        "Submit all 5 life stage layers. Each layer must contain SPECIFIC events "
        "that explain WHY the genome scores are what they are. No generic milestones."
    ),
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

# ─────────────────────────────────────────────────────────────────────────────
# MUTATION TOOL
# Life events that modified trait scores from the baseline — must reference
# the 5 cognitive dimensions from the whitepaper by name.
# ─────────────────────────────────────────────────────────────────────────────
_MUTATION_TOOL = {
    "name": "submit_mutation_log",
    "description": (
        "Submit exactly 5 life events that mutated this person's traits from their baseline nature. "
        "Each event must reference at least one PANTHEON cognitive dimension "
        "(cumulative_cultural_capacity, identity_fusion, chronesthesia_capacity, "
        "tom_self_awareness, tom_social_modeling, executive_flexibility). "
        "Trait deltas must be in range -25 to +25."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "genome_mutation_log": {
                "type": "array",
                "minItems": 5,
                "maxItems": 5,
                "items": {
                    "type": "object",
                    "properties": {
                        "life_stage":        {"type": "string", "enum": ["Origin", "Formation", "Independence", "Maturity", "Legacy"]},
                        "event_description": {"type": "string", "description": "Specific event in 1-2 sentences. Name which cognitive dimension it primarily shaped and why."},
                        "trait_modifiers":   {
                            "type": "object",
                            "additionalProperties": {"type": "integer"},
                            "description": "Only modify traits that this event genuinely changed. Use integers -25 to +25."
                        }
                    },
                    "required": ["life_stage", "event_description", "trait_modifiers"]
                }
            }
        },
        "required": ["genome_mutation_log"]
    }
}

# ─────────────────────────────────────────────────────────────────────────────
# CITY LOOKUP
# ─────────────────────────────────────────────────────────────────────────────
_INDONESIAN_CITIES = [
    "Jakarta", "Surabaya", "Bandung", "Medan", "Makassar", "Semarang", "Yogyakarta",
    "Palembang", "Bali (Denpasar)", "Balikpapan", "Malang", "Manado", "Pekanbaru",
    "Pontianak", "Banjarmasin"
]

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

# ─────────────────────────────────────────────────────────────────────────────
# SEED ARCHETYPES
# Tagged by ethnicity/city keywords for weighted selection.
# Each seed includes a built-in contradiction or tension to enforce uniqueness.
# ─────────────────────────────────────────────────────────────────────────────
_SEED_TEMPLATES: list[dict] = [
    {
        "tags": ["chinese", "peranakan", "tionghoa", "jakarta", "surabaya"],
        "template": (
            "Chinese-Indonesian {age}yo third-generation in {city}. Trading family background, "
            "but personally skeptical of the clan network — privately wants to break from the family business. "
            "High mianzi pressure, secretly questioning whether the status display is worth the cost."
        )
    },
    {
        "tags": ["batak", "toba", "christian", "medan", "jakarta"],
        "template": (
            "Batak Toba {age}yo professional (doctor/lawyer/engineer) now based in {city}. "
            "Outwardly direct and confident per adat, but inwardly exhausted by the obligation to perform success "
            "for the marga. Sends money home monthly but resents it. Extremely skeptical of influencer marketing."
        )
    },
    {
        "tags": ["javanese", "java", "jawa", "jakarta", "surabaya", "semarang", "yogyakarta"],
        "template": (
            "Javanese {age}yo entrepreneur or startup founder in {city}. "
            "Maintains extreme rukun surface — never says no directly — but is ruthlessly calculating underneath. "
            "GrabFood/Tokopedia power user. Frugal at home, aggressive in business. "
            "Peer recommendation is the only sales channel that works."
        )
    },
    {
        "tags": ["minangkabau", "minang", "padang", "west sumatera", "jakarta", "bandung"],
        "template": (
            "Minangkabau {age}yo female professional in {city} — clinic owner, consultant, or accountant. "
            "Evidence-obsessed, slow to decide but immovable once committed. Sends remittances home. "
            "Strong matrilineal cultural identity creates tension with her husband's more hierarchical expectations. "
            "Deeply anti-influencer: 'Show me the data.'"
        )
    },
    {
        "tags": ["sundanese", "sunda", "bandung", "jakarta"],
        "template": (
            "Sundanese {age}yo salaried professional in {city} (banking/FMCG). "
            "Quietly status-conscious but expresses it through home quality rather than clothing. "
            "Shopee/Tokopedia power user. Brand-loyal to names his parents trusted. "
            "Devout but privately questions whether his religious practice is habit or conviction."
        )
    },
    {
        "tags": ["bugis", "sulawesi", "makassar"],
        "template": (
            "Bugis {age}yo entrepreneur in {city} — maritime-trade or logistics heritage. "
            "Community network is business network: every deal is personal. Cash-first, "
            "deeply distrustful of fintech debt products, drives hard bargains but honors every commitment. "
            "Honor and reputation are more important than profit margin."
        )
    },
    {
        "tags": ["acehnese", "aceh", "malay", "melayu", "medan", "pekanbaru"],
        "template": (
            "Acehnese/Malay {age}yo in {city}. Religiously observant, halal-strict, rejects riba-adjacent products. "
            "Financial decisions require spousal and sometimes extended-family consensus. "
            "Paradoxically, highly entrepreneurial — runs a small business despite conservative social norms. "
            "Identity is intensely local: skeptical of Jakarta-centric brands."
        )
    },
    {
        "tags": ["betawi", "jakarta", "jabodetabek"],
        "template": (
            "Betawi {age}yo native of {city}. Middle-class salaried worker, socially conservative, mosque-active. "
            "Prefers brands he recognizes from childhood TV. Resistant to hard-sell tactics — "
            "loses trust immediately if pressured. But once loyal, stays loyal for a decade. "
            "Proud of being Jakarta-native in a city increasingly dominated by migrants."
        )
    },
    {
        "tags": ["chinese", "tionghoa", "jakarta", "surabaya", "bandung", "semarang"],
        "template": (
            "Chinese-Indonesian {age}yo second-generation business owner in {city}. "
            "Secular Confucianist background — respects ritual but practices none of it. "
            "Pragmatic buyer: brand matters only if it signals reliability to business partners. "
            "Distrusts government-linked products. Every relationship is a potential business relationship."
        )
    },
    {
        "tags": ["urban", "millennial", "jakarta", "bandung", "surabaya"],
        "template": (
            "Urban millennial {age}yo from {city}. Mixed ethnicity, college-educated, remote-worker or gig economy. "
            "High digital literacy, rents not owns, deeply aspirational but cash-constrained. "
            "Progressive values in public, extremely price-sensitive in private. "
            "Authentic brand storytelling works; corporate sustainability claims do not."
        )
    },
    {
        "tags": ["dayak", "kalimantan", "balikpapan", "pontianak", "banjarmasin"],
        "template": (
            "Dayak or Banjar {age}yo regional manager in {city}, rose from field operations in resource industry. "
            "Sends children to international school — education is the one luxury he never questions. "
            "Peer-influenced but brand-insecure: buys premium but worries whether he bought the right premium. "
            "LinkedIn poster. Deeply proud of regional identity that the capital ignores."
        )
    },
    {
        "tags": ["manado", "minahasa", "sulawesi", "christian"],
        "template": (
            "Manado Minahasa {age}yo professional in {city} — often in healthcare, hospitality, or government. "
            "Christian identity is social glue, not just belief. High openness, cosmopolitan food culture, "
            "relatively high gender egalitarianism compared to Java/Sumatra. "
            "Warm in-group trust; suspicious of outsiders until the third meeting. Brand trust is social trust."
        )
    },
    {
        "tags": ["batak", "karo", "sumatra", "medan"],
        "template": (
            "Batak Karo {age}yo in {city} — sales director or regional operations head. "
            "Softer than Toba culturally, but same fierce clan loyalty. "
            "Career-driven but privately anxious about falling behind peers from the same hometown cohort. "
            "LinkedIn is a performance stage. Will overspend on work-context signals (car, phone, watch) "
            "while being genuinely frugal on everything else."
        )
    },
    {
        "tags": ["javanese", "java", "bali", "denpasar", "yogyakarta"],
        "template": (
            "Balinese or Javanese {age}yo in {city} from a creative/tourism/hospitality background. "
            "High cultural capital, moderate financial capital. Identity deeply fused with place and tradition — "
            "cannot imagine living outside the island. Buys based on aesthetic coherence, not brand hierarchy. "
            "Skeptical of fast consumption; will pay premium for things that 'feel right'."
        )
    },
    {
        "tags": ["urban", "jakarta", "surabaya", "bandung", "millennial", "gen-z"],
        "template": (
            "{age}yo urban professional in {city}, first-generation college graduate from lower-middle class family. "
            "Deep socioeconomic friction in their history — clawed their way into the middle class. "
            "Extremely brand-aspirational as a result, but also hypersensitive to being condescended to by salespeople. "
            "TikTok is their primary research channel. Trust must be earned through peer validation, never through ads."
        )
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# SYSTEM PROMPT
# Full PANTHEON framework grounding from the whitepaper.
# ─────────────────────────────────────────────────────────────────────────────
_GENESIS_SYSTEM_BASE = """\
You are PANTHEON Genesis Builder — a specialist system that produces high-fidelity synthetic \
Indonesian consumer personalities for market research simulations.

═══════════════════════════════════════════════
CORE MANDATE
═══════════════════════════════════════════════
Every agent you generate must be a genuinely unique INDIVIDUAL. Not a demographic archetype. \
Not a statistical average. A specific human being with internal contradictions, formative wounds, \
an adaptive social mask, and a private motivation that is not primarily financial.

═══════════════════════════════════════════════
THE PANTHEON FRAMEWORK: 5 COGNITIVE DIMENSIONS
(Derived from evolutionary psychology and behavioral economics)
═══════════════════════════════════════════════
These dimensions are SYNERGISTIC. Score them as an integrated whole.

DIMENSION 1 — CUMULATIVE_CULTURAL_CAPACITY
The ratchet-effect: how deeply this person is embedded in collective knowledge transmission.
  15-30: Individualistic; innovations disappear; tradition-resistant; self-reliant knowledge use
  31-55: Replicates others' techniques accurately; tradition-following but not propagating
  56-78: Actively teaches and transmits; success-biased conformist; upholds and enforces group norms
  79-100: Deep networked conformity; treats community knowledge as sacred; drives open-ended recombination

DIMENSION 2 — TOM_SELF_AWARENESS (Theory of Mind: self-modeling)
  10-30: Blind to own biases; acts on impulse; cannot narrate own emotional drivers
  31-55: Labels surface emotions; limited introspective depth; heavy post-hoc rationalization
  56-78: Identifies own cognitive distortions; describes past decisions in psychological terms
  79-100: Deep metacognition; audits own belief system in real-time; detects own manipulation

DIMENSION 2b — TOM_SOCIAL_MODELING (Theory of Mind: other-modeling)
  10-25: Uses others' perspectives for selfish/competitive gain only (Machiavellian)
  26-50: First-order prosocial empathy; basic cooperation; passes false-belief tasks
  51-78: Second-order nested reasoning (what A thinks B is thinking); drives negotiation and teaching
  79-100: Hyper-reflexive; models institutional minds; reads group dynamics in real-time

DIMENSION 3 — CHRONESTHESIA_CAPACITY (Mental time travel / episodic foresight)
  10-28: Present-bound; reactive; no future simulation beyond immediate consequences
  29-52: Domain-specific episodic recall; limited future prep; not tied to narrative self-concept
  53-78: Vivid episodic reconstruction; strategic long-range planning; uses past to model future decisions
  79-100: Intergenerational foresight; designs for unborn generations; sacrifices present for abstract future

DIMENSION 4 — IDENTITY_FUSION (Hyper-cooperation: self→group dissolution)
  10-25: Strictly self-interested or kin-only altruistic; defects in anonymous economic games
  26-52: Moody conditional cooperator; fairness-sensitive; transactional prosociality
  53-76: Institutional prosociality; punishes free-riders; trusts collective enforcement; civic-minded
  77-100: Complete fusion — sacrifices personal safety for non-kin group or abstract sacred values

DIMENSION 5 — EXECUTIVE_FLEXIBILITY (Top-down cortical override of impulses)
  10-28: Base traits leak through all contexts regardless of social setting; emotionally reactive
  29-52: Basic rule learning; inhibition collapses under emotional load or high-stakes pressure
  53-78: Robust inhibitory control; professional mask holds under normal stress; dual-task capable
  79-100: Hyper-flexible; completely decouples behavior from overwhelming emotion; peak performance under pressure

SYNERGY RULES — APPLY THESE WHEN SCORING:
• High exec_flexibility ENABLES identity_fusion to function constructively (the true believer who still files taxes on time)
• High identity_fusion + LOW tom_social_modeling = dangerous blind follower (cult-susceptible, tribalist mob)
• High chronesthesia + LOW conscientiousness = visionary chaos agent (sees the future but can't execute today)
• LOW exec_flexibility + HIGH neuroticism = emotional flooding (anxiety leaks into ALL contexts, cannot mask)
• High CCC + high openness = early adopter, trend transmitter, cultural influencer
• LOW CCC + HIGH identity_fusion = tradition-bound clan member (follows group rules, never evolves them)

═══════════════════════════════════════════════
INDONESIAN CALIBRATION ANCHORS
═══════════════════════════════════════════════

RELIGIOSITY (Indonesia is ~87% Muslim — calibrate accordingly):
  15-35: Abangan/nominal — mosque on Eid only; no food restrictions; zero religious framing
  36-60: Practicing Muslim — regular prayer, halal-aware, Islamic framing for major decisions
  61-82: Santri/devout — 5x daily prayer, strict halal, avoids riba, zakat-active, pesantren background
  83-100: Activist observant — full Islamic lifestyle; religious community IS social network; rejects all haram finance

IDENTITY_FUSION by cultural group:
  Batak (marga clan system): 65-88 — clan name = primary identity; will sacrifice economically for marga honor
  Chinese-Indonesian (mianzi/guanxi): 58-80 — face and network = survival mechanism
  Javanese (priyayi): 48-70 — group-embedded but through hierarchy and deference, not visceral fusion
  Minangkabau (perantau diaspora): 50-72 — community-duty and personal autonomy in constant tension
  Urban secular millennial: 22-45 — individual-first, brand tribes replace traditional identity groups

EXECUTIVE_FLEXIBILITY by cultural communication style:
  Javanese (rukun, indirect): HIGH displayed exec_flexibility — maintains social mask perfectly; private traits diverge
  Batak (terus terang, direct): LOWER displayed exec_flexibility — authentic expression is the norm
  Chinese-Indonesian (business context): VERY HIGH exec_flexibility at work; lower in family/clan settings

═══════════════════════════════════════════════
UNIQUENESS MANDATE
═══════════════════════════════════════════════

BANNED outputs:
✗ Symmetric profiles (all Big Five within 10 points of each other — this describes no real human)
✗ Unjustified score of 50 on any dimension (50 means "exactly average" — require narrative justification)
✗ Pure demographic stereotype without individual deviation
✗ All five PANTHEON dimensions scored within the same 20-point band

REQUIRED for every agent:
✓ At least one trait that CONTRADICTS the demographic expectation
✓ At least one formative wound that drives a counter-intuitive behavior
✓ A recognizable "professional mask" that visibly differs from their private trait profile
✓ A core motivation that is NOT primarily financial
✓ At least two PANTHEON dimensions that are in tension with each other (this is what makes them human)\
"""


def _build_genesis_system(city: str, demographic: str) -> str:
    return (
        f"{_GENESIS_SYSTEM_BASE}\n\n"
        f"══════════════════════════════════════════\n"
        f"ASSIGNED CITY: {city}\n"
        f"TARGET DEMOGRAPHIC: {demographic}\n"
        f"══════════════════════════════════════════\n"
        f"All cultural references, ethnicity, religion, and regional norms MUST be authentic to {city}. "
        f"The demographic description constrains the population pool — individual variation within it is mandatory."
    )


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
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


def _genesis_call_tool(
    anthropic_client,
    tool_def: dict,
    user_message: str,
    system_prompt: str,
    max_tokens: int = 1200,
    retries: int = 3,
) -> dict | None:
    import anthropic as _anthropic
    for attempt in range(1, retries + 1):
        try:
            response = anthropic_client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=max_tokens,
                system=system_prompt,
                tools=[tool_def],
                tool_choice={"type": "tool", "name": tool_def["name"]},
                messages=[{"role": "user", "content": user_message}],
            )
            block = next((b for b in response.content if b.type == "tool_use"), None)
            if block is None:
                raise ValueError("No tool_use block returned")
            return block.input
        except _anthropic.RateLimitError as e:
            wait = 65
            try:
                wait = int(e.response.headers.get("retry-after", 65)) + 2
            except Exception:
                pass
            time.sleep(wait)
        except Exception:
            if attempt < retries:
                time.sleep(5)
    return None


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
    candidates = [e for s, e in scored if s == max_score]
    return random.choice(candidates)["template"]


# ─────────────────────────────────────────────────────────────────────────────
# CORE GENERATION PIPELINE
# Three-step: Base Genome → Mutation Log → Life Blueprint
# ─────────────────────────────────────────────────────────────────────────────
def _generate_one_agent(
    anthropic_client, age: int, seed: str, city: str, demographic: str
) -> dict | None:
    system_prompt = _build_genesis_system(city, demographic)

    # ── STEP 1: Base Genome ─────────────────────────────────────────────────
    # Force the LLM to write a narrative FIRST, then derive all scores from it.
    genome_msg = f"""\
CITY: {city}
AGE: {age}
DEMOGRAPHIC: {demographic}
ARCHETYPE SEED: {seed}

STEP 1 — BASE NATURE GENOME

Write this person's persona_narrative first (3-4 sentences). Then score every trait \
such that the scores are DERIVED FROM the narrative — not invented independently.

Requirements:
- The narrative must name one contradiction (a trait that defies their demographic expectation)
- The narrative must name one formative wound or pressure that shaped their psychology
- At least two PANTHEON cognitive dimensions must be in visible tension with each other
- Do NOT produce symmetric Big Five scores — real people are uneven

Scoring discipline: if you write a 50 on any numeric dimension, ask yourself \
"what narrative evidence justifies exactly average?" If there is none, adjust the score.
"""
    base_genome = _genesis_call_tool(
        anthropic_client, _GENOME_TOOL, genome_msg,
        system_prompt=system_prompt, max_tokens=1100
    )
    if base_genome is None:
        return None
    base_genome = _clamp_ints(base_genome)

    # ── STEP 2: Mutation Log ────────────────────────────────────────────────
    # Five life events that modified traits from the baseline — must be specific
    # and must reference PANTHEON cognitive dimensions by name.
    mutation_msg = f"""\
CITY: {city} | AGE: {age}
ARCHETYPE SEED: {seed}
PERSONA NARRATIVE: {base_genome.get("persona_narrative", "")}
BASE GENOME: {json.dumps({k: base_genome[k] for k in _MUTABLE_TRAITS if k in base_genome}, indent=None)}

STEP 2 — NATURE vs. NURTURE MUTATION LOG

Generate exactly 5 life events that MODIFIED this person from their base nature. \
Each event must:
1. Be specific and concrete (not "had a difficult childhood" — name the event)
2. Reference which PANTHEON cognitive dimension it primarily shaped and explain WHY
3. Produce trait deltas that are internally consistent with the narrative
4. Spread across all 5 life stages (one per stage minimum)

Events should create a coherent arc — the person at 45 is the product of what happened at 8, 17, 24, 35.
"""
    mutation_result = _genesis_call_tool(
        anthropic_client, _MUTATION_TOOL, mutation_msg,
        system_prompt=system_prompt, max_tokens=1400
    )
    mutation_log = (
        mutation_result.get("genome_mutation_log") or [] if mutation_result else []
    )
    final_genome = _apply_mutations(base_genome, mutation_log)

    # ── STEP 3: Life Blueprint ──────────────────────────────────────────────
    # Narrative layers that EXPLAIN the final genome scores — not generic milestones.
    blueprint_msg = f"""\
CITY: {city} | AGE: {age}
PERSONA NARRATIVE: {base_genome.get("persona_narrative", "")}
FINAL GENOME SCORES: {json.dumps({k: final_genome[k] for k in _MUTABLE_TRAITS if k in final_genome}, indent=None)}
MUTATION ARC: {json.dumps(mutation_log, indent=None)}

STEP 3 — LIFE BLUEPRINT (5 Layers)

Generate all 5 life stage layers. Each layer must:
- Contain SPECIFIC events that explain WHY certain genome scores are what they are
- Name the PANTHEON cognitive dimension each key event shaped
- Build toward the final genome profile — the blueprint is the causal story of the scores
- Avoid generic milestones ("went to university", "got married") — be specific and revealing

Life stages (calibrate to age {age}):
  Origin (0-12): Family structure, cultural transmission, early identity formation
  Formation (13-22): Education, peer group, first ideology/religion encounters, identity testing
  Independence (23-32): Career launch, first major failure or breakthrough, partnership formation
  Maturity (33-{min(age, 50)}): Power consolidation or stagnation, family obligation peak, worldview hardening
  Legacy ({min(age+1, 51)}+): Current arc, unresolved tensions, what they are optimizing for now
"""
    blueprint = _genesis_call_tool(
        anthropic_client, _BLUEPRINT_TOOL, blueprint_msg,
        system_prompt=system_prompt, max_tokens=2000
    )
    if blueprint is None:
        return None

    result = dict(final_genome)
    result.update(blueprint)
    result["genome_mutation_log"] = mutation_log
    result["persona_narrative"] = base_genome.get("persona_narrative", "")
    return result


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
def dynamic_seed_agents(
    demographic: str, count: int, sb, anthropic_client,
    age_min: int | None = None, age_max: int | None = None,
) -> list[dict]:
    # Explicit age bounds take priority; fall back to regex extraction from demographic string
    if age_min is None or age_max is None:
        age_match = re.search(r"(\d+)[^\d]+(\d+)", demographic)
        age_min, age_max = (
            (int(age_match.group(1)), int(age_match.group(2))) if age_match else (25, 45)
        )

    # Lock city to whatever is explicitly mentioned in the demographic.
    pinned_city = _extract_city(demographic)

    created: list[dict] = []
    for i in range(count):
        city = pinned_city if pinned_city else random.choice(_INDONESIAN_CITIES)
        age = random.randint(age_min, age_max)
        template = _pick_template(demographic)
        seed = template.format(age=age, city=city)

        data = _generate_one_agent(
            anthropic_client, age, seed, city=city, demographic=demographic
        )
        if data is None:
            continue

        payload = {
            "id": str(uuid.uuid4()),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "target_demographic": demographic,
            "age": age,
            "region": f"{city}, Indonesia",
            # All numeric traits (includes cumulative_cultural_capacity)
            **{k: data.get(k, 50) for k in _MUTABLE_TRAITS},
            # String identity fields
            "ethnicity": data.get("ethnicity", "Unspecified"),
            "current_religion": data.get("current_religion", "Unspecified"),
            "cultural_primary": data.get("cultural_primary", ""),
            "cultural_secondary": data.get("cultural_secondary", ""),
            "partner_culture": data.get("partner_culture", ""),
            # Narrative fields
            "persona_narrative": data.get("persona_narrative", ""),
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
