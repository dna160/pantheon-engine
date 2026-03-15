---
name: pantheon-app
description: Use this skill when the user is working on the PANTHEON synthetic focus group app — including building or debugging main.py, seeding agent genomes, writing SQL for Supabase, orchestrating the Modal pipeline, designing prompts for PANTHEON agents, or discussing the 5-node execution architecture. Also triggers when the user references "agent genomes", "genome builder", "Phase A/B/C", "breakout rooms", "synthesis report", "genome_culture", "cultural profile", "religious conversion", or "PANTHEON".
version: 3.0.0
---

# PANTHEON App — Developer Skill

## What PANTHEON Is

PANTHEON is an AI-powered synthetic focus group simulator. It generates hyper-realistic simulated human agents ("genomes"), runs them through a structured 3-phase focus group protocol, and produces a 7-section Research Intelligence Report for campaign evaluation.

**Stack:** Python · Supabase (PostgreSQL) · Modal (serverless) · Anthropic Claude API · pptxgenjs (Node.js)

---

## The 5-Node Execution Pipeline (`main.py`)

Each node is a Modal `@app.function` decorator.

| Node | Name | Model | Concurrency |
|------|------|-------|-------------|
| 1 | Intake & Query | — | Synchronous |
| 2 | Runtime Snapshot | `claude-haiku-4-5-20251001` | Parallel `.map()` |
| 3 | Phase A — Mass Session | `claude-haiku-4-5-20251001` | Parallel `.starmap()` |
| 4 | Phase B — Breakout Rooms | `claude-sonnet-4-5` | Grouped `.starmap()` |
| 5 | Phase C — Synthesis | `claude-sonnet-4-5` | Single heavy call |

**Node 6** (local, post-pipeline): Reads the Phase C `.md` report → calls Claude Sonnet (`extract_deck_content` tool) → generates `.pptx` via pptxgenjs.

### Node 1 — Intake & Query
```sql
SELECT * FROM agent_genomes WHERE target_demographic = [Target] LIMIT 100
```
Also indexes on `age` for runtime snapshot injection.

### Node 2 — Runtime Snapshot
- Injects JSONB life layers matching the agent's `age`
- Calculates: current emotional state, mental bandwidth, financial pressure
- Uses `claude-haiku-4-5-20251001`

### Node 3 — Phase A (Mass Session)
- Input: dynamic snapshots + campaign brief
- Enforced JSON output schema:
  - `gut_reaction` (string)
  - `emotional_temperature` (integer 1–10)
  - `personal_relevance_score` (integer 1–10)
  - `intent_signal` (string)

### Node 4 — Phase B (Breakout Rooms)
- Groups of 5 agents, composed for productive friction
- Each group gets all Phase A reactions as shared context
- Simulates multi-turn spoken debate in each agent's authentic voice
- Uses `claude-sonnet-4-5` for richer reasoning

### Node 5 — Phase C (Synthesis)
- Inputs: all Phase A reactions + all Phase B transcripts
- Uses `claude-sonnet-4-5`
- Produces the 7-section **Research Intelligence Report**:
  1. The Headline Truth
  2. PTM Signal Analysis
  3. STM Signal Analysis
  4. The Fracture Lines
  5. The Invisible Insight
  6. The Three Sharpening Recommendations
  7. The Kill Switch

---

## Database Schema (`agent_genomes` table)

### Metadata Columns
| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | PK, `uuid_generate_v4()` |
| `created_at` | TIMESTAMP | default `now()` |
| `target_demographic` | VARCHAR | **Indexed** — e.g. `'Urban Millennial'` |
| `age` | INTEGER | **Indexed** |
| `region` | VARCHAR | |

### Cultural & Religious Profile Columns *(new in v2)*
| Column | Type | Notes |
|--------|------|-------|
| `ethnicity` | VARCHAR | **Indexed** — e.g. `'Batak Toba'`, `'African American'` |
| `cultural_primary` | VARCHAR | Primary cultural identity (usually same as ethnicity) |
| `cultural_secondary` | VARCHAR | Secondary cultural identity if bicultural (nullable) |
| `religion_of_origin` | VARCHAR | Religion raised in — e.g. `'Protestant'`, `'Islam (Devout)'` |
| `current_religion` | VARCHAR | **Indexed** — religion now (may differ if converted) |
| `religiosity` | INT | **Indexed** — 1=atheist/secular · 100=fundamentalist devout |
| `partner_culture` | VARCHAR | nullable — partner's ethnicity if intercultural relationship |
| `partner_religion` | VARCHAR | nullable — partner's religion if different from agent |

### Personality Genome — Big Five + Behavioral Traits (INT 1–100)
All sliders represent a continuous spectrum:

| Column | Spectrum |
|--------|----------|
| `openness` | Rigidly traditional ↔ Radically curious |
| `conscientiousness` | Chaotically spontaneous ↔ Obsessively structured |
| `extraversion` | Deeply internal ↔ Compulsively social |
| `agreeableness` | Confrontational ↔ Peace-seeking |
| `neuroticism` | Unshakably calm ↔ Chronically anxious |
| `communication_style` | Blunt/terse ↔ Diplomatic/verbose |
| `decision_making` | Gut instinct ↔ Analytical paralysis |
| `brand_relationship` | Skeptical/anti-brand ↔ Brand-loyal evangelist |
| `influence_susceptibility` | Immune to social proof ↔ Heavily peer-influenced |
| `emotional_expression` | Stoic/reserved ↔ Explosive/transparent |
| `conflict_behavior` | Avoidant ↔ Confrontational |
| `literacy_and_articulation` | 1=barely literate · 100=eloquent/highly educated |
| `socioeconomic_friction` | 1=comfortable trajectory · 100=severe systemic barriers |

### Cognitive Architecture Traits *(new in v3)* (INT 1–100)

| Column | Spectrum | What it drives |
|--------|----------|----------------|
| `identity_fusion` | Pure individualist ↔ Visceral group oneness | When agents sacrifice personal utility for group honor/face (mianzi, marga, guanxi, familismo) |
| `chronesthesia_capacity` | Present-only thinker ↔ Vivid mental time traveler | Whether decisions reference future projections vs. immediate stimuli |
| `tom_self_awareness` | Blind to own states ↔ Deep self-reflection | First-order Theory of Mind — how accurately agents reflect on their own emotions/biases |
| `tom_social_modeling` | Oblivious to others ↔ Reads rooms perfectly | Second-order Theory of Mind — how agents model what others think of them |
| `executive_flexibility` | Traits leak always ↔ Can override impulses | Gap between inner thought and spoken word in social contexts |

### Trait Generation Architecture *(v3)*

**Base genome** uses gaussian distribution N(50, 15) with trait covariance:
- `decision_making` positively correlated with `conscientiousness` (r≈0.4)
- `emotional_expression` positively correlated with `extraversion` (r≈0.5)
- `conflict_behavior` negatively correlated with `agreeableness` (r≈-0.6)
- Cognitive architecture traits are independent at base, culturally modified

**Age-graded developmental drift** (`apply_age_drift`) applies before cultural modifiers:
- Conscientiousness: +0.3/yr after 20 (maturity)
- Agreeableness: +0.2/yr after 25
- Neuroticism: -0.2/yr after 30
- Openness: -0.1/yr after 35
- Chronesthesia: +0.15/yr after 25 (foresight matures)
- Executive flexibility: inverted-U peak in middle age

**Pipeline order**: base genome (gaussian) → age drift → cultural modifiers → mutation log

> **Cultural modifiers**: `literacy_and_articulation` and `socioeconomic_friction` are generated from ethnicity-grounded ranges (not random 1–100) in `genome_culture.py`. All other genome traits start gaussian and are shifted by cultural, religiosity, intercultural marriage, and conversion modifiers.

### 100-Year Life Blueprint (JSONB columns)
Queried at runtime by the agent's `age` to extract relevant life layers.

| Column | Life Stage | Years | Notes |
|--------|-----------|-------|-------|
| `origin_layer` | Birth, family, attachment | 0–5 | |
| `formation_layer` | Education, adolescence, beliefs | 5–18 | |
| `independence_layer` | Career, relationships, consumer psychology | 18–35 | |
| `maturity_layer` | Mid-life, worldview, health | 35–60 | |
| `legacy_layer` | Aspirational projection | 60–100 | *(v3)* Now represents CURRENT future projection, not fixed destiny. For agents <60, replaced by chronesthesia directive during simulation. |

### Voice Print (JSONB)
```json
{
  "vocabulary_level": "string",
  "filler_words": ["string", "string", "string"],
  "cultural_speech_markers": ["string", "string"],
  "religious_language": ["string", "string"],
  "persuasion_triggers": ["string", "string", "string"],
  "conflict_style": "string"
}
```
- `cultural_speech_markers`: dialect patterns, code-switching, borrowed phrases (e.g. `"lah bah"` for Batak Toba, `"aiyah"` for Chinese-Indonesian, AAVE patterns for African American)
- `religious_language`: faith expressions calibrated to `religiosity` score (e.g. `"insyaAllah"` for devout Muslims, empty/ironic for secular agents)

### Genome Mutation Log (JSONB)
Array of life events that shifted the genome from baseline toward its final scores.

**Structure of each entry:**
```json
{
  "life_stage": "Origin/Formation | Formation | Independence | Maturity | Legacy",
  "event_description": "string",
  "trait_modifiers": { "openness": 10, "neuroticism": -5 }
}
```

**Composition in the seeder:**
- **Entries 1–N** (prepended by `genome_culture.py`): cultural upbringing, bicultural identity, intercultural marriage, religious conversion — pre-determined facts with precise trait_modifiers
- **Entries N+1 onwards** (generated by Claude): non-cultural life events (divorce, job loss, illness, trauma, academic failure, etc.) with approximate directional trait_modifiers

An empty array `[]` means a completely stable, culturally-normative life with no major mutations.

---

## Cultural & Religious Engine (`genome_culture.py`)

The engine that runs **before** Claude is called in the seed scripts.

### Generation Flow *(v3 — gaussian + age drift)*

```
region + age
    │
    ├── generate_base_genome()               ← gaussian(50,15) + trait covariance
    │       └── Big Five: independent gaussian draws
    │       └── Behavioral traits: derived from Big Five (r≈0.4–0.6)
    │       └── 5 cognitive traits: independent gaussian
    │
    ├── apply_age_drift(genome, age)          ← developmental psychology curves
    │       └── conscientiousness +0.3/yr after 20
    │       └── agreeableness +0.2/yr after 25
    │       └── neuroticism -0.2/yr after 30
    │       └── chronesthesia_capacity +0.15/yr after 25
    │       └── executive_flexibility inverted-U peak mid-life
    │
    ├── weighted_choice(ETHNICITY_POOLS)  →  ethnicity
    │       └── 12% chance bicultural     →  cultural_secondary
    │
    ├── weighted_choice(RELIGION_BY_ETHNICITY[ethnicity])  →  religion_of_origin
    │
    ├── random(RELIGIOSITY_RANGES[religion])  →  religiosity
    │
    ├── random < INTERCULTURAL_MARRIAGE_PROB  →  partner_culture, partner_religion
    │
    ├── _determine_conversion()  →  current_religion, conv_type, conv_age
    │       └── rolls CONVERSION_MAP probabilities
    │           └── doubled if has_intercultural_partner (pressure)
    │
    ├── random(SOCIOECONOMIC_FRICTION_RANGES[ethnicity])  →  socioeconomic_friction
    ├── random(LITERACY_RANGES[ethnicity])                →  literacy_and_articulation
    │
    ├── accumulate CULTURE_MODIFIERS + RELIGIOSITY_MODIFIERS +
    │   INTERCULTURAL_MARRIAGE_MODIFIERS + CONVERSION_MODIFIERS
    │
    ├── build cultural_mutation_events (2–4 pre-built mutation log entries)
    │
    └── build cultural_context_for_prompt (injected into Claude user message)
```

### Ethnicity Pools

**Medan, Indonesia** (by weight):
Batak Toba 22% · Chinese-Indonesian 16% · Javanese 12% · Malay Deli 10% · Batak Karo 10% · Minangkabau 9% · Acehnese 8% · Nias 4% · Batak Simalungun 5% · Mixed Ethnic 4%

**North America** (by weight):
White non-Hispanic 57% · Hispanic/Latino 19% · African American 13% · Asian American 6% · Mixed/Multiracial 5%

### Religion by Ethnicity (examples)
| Ethnicity | Religion Distribution |
|-----------|----------------------|
| Batak Toba | Protestant 80% · Catholic 15% · Islam 5% |
| Chinese-Indonesian | Protestant 38% · Buddhist/Taoist 30% · Catholic 22% · None 8% |
| Acehnese | Islam (Devout) 96% · Islam (Nominal) 4% |
| Javanese | Islam (Nominal) 52% · Islam (Devout) 38% · Protestant 5% |
| White non-Hispanic | Protestant 38% · None/Agnostic 26% · Catholic 22% · Atheist 7% |
| African American | Protestant 72% · Islam 9% · Catholic 8% · None 9% |
| Hispanic/Latino | Catholic 58% · Protestant 22% · None 17% |
| Asian American | None/Agnostic 26% · Protestant 26% · Buddhist 15% · Hindu 10% |

### Religious Conversion Probabilities
Based on Pew Research Center (2015, 2021) and Indonesian CRCS studies.

**Key rates (lifetime probability):**
| From | To | Probability | Context |
|------|----|-------------|---------|
| Protestant | None/Agnostic | 28% | North American millennial deconversion |
| Catholic | None/Agnostic | 24% | Same trend |
| Buddhist (Indonesia) | Protestant | 13% | Urban evangelism |
| Protestant | Islam | 7% | Medan intercultural marriage |
| Jewish | None/Agnostic | 20% | Generational drift |
| Islam | Protestant | 0.8% | Rare — social and legal barriers |
| Islam | None/Agnostic | 6% | Urban educated drift |

**Conversion types and personality impact:**

| Type | Trigger | Key trait shifts |
|------|---------|-----------------|
| `secular_drift` | Education/urbanization | openness +18, conscientiousness -8 |
| `to_devout` | Revival/grief/mentor | conscientiousness +16, openness -16 |
| `genuine_conversion` | Spiritual seeking | conscientiousness +11, neuroticism -13 |
| `interfaith_marriage_pressure` | Required for marriage | neuroticism +22, agreeableness -6 |

> **Intercultural marriage doubles conversion probability** — the most realistic pressure mechanic.

### Culture Personality Modifiers (examples)
| Ethnicity | Notable shifts |
|-----------|---------------|
| Batak Toba | extraversion +12, conflict_behavior +10, conscientiousness +8 (direct, ambitious) |
| Javanese | agreeableness +14, conflict_behavior -14, communication_style +12 (face-saving) |
| Chinese-Indonesian | conscientiousness +14, emotional_expression -12, brand_relationship +10 |
| Acehnese | conscientiousness +12, openness -12 (deeply conservative) |
| African American | extraversion +9, emotional_expression +12 |
| Asian American | conscientiousness +14, emotional_expression -12, conflict_behavior -9 |

### Religiosity Modifiers
Applied if `religiosity >= 60` (devout) or `<= 28` (secular):

| State | Key shifts |
|-------|-----------|
| Devout (60+) | conscientiousness +13, openness -13, agreeableness +9, neuroticism -8 |
| Secular (≤28) | openness +13, decision_making +9, conscientiousness -6 |

---

## PANTHEON System Prompt — Operating Philosophy

When writing prompts for PANTHEON or any of its agents, apply these principles:

### The Three Laws
1. **Irreducible Uniqueness** — No two agents share the same formative experiences, personality architecture, or worldview.
2. **Authentic Friction** — Agents disagree, change their minds, hold contradictions, and sometimes refuse to engage. Consensus is a failure state.
3. **Non-Interference** — Never guide agents toward a desired outcome. The room is more valuable than the campaign.

### The Mirror Test
Every agent must pass: if a research director read the profile alongside a real interview transcript, they should not be able to tell which is which.

### Cultural Coherence Rule *(v2 addition)*
The cultural/religious profile is a **hard constraint**, not a suggestion. Life layers must honour:
- The ethnic community's social norms and communication patterns
- The religiosity level's influence on decision-making and worldview
- The specific friction points of intercultural marriage or conversion (if applicable)
- The voice_print must carry authentic dialect markers and faith-language calibrated to religiosity

### Agent Genesis Layers (for Genome Builder prompts)
- **Origin** (0–5): birth, family structure, attachment style, cultural household
- **Formation** (5–18): education, formative friendships, religious formation, adolescent crucibles
- **Independence** (18–35): career, finances, identity evolution, consumer bonding, intercultural encounters
- **Maturity** (35–60): life plateau or breakthrough, worldview solidification, faith deepening or erosion
- **Legacy** (60+): technology relationship, regrets, mortality

---

## Genome Builder (seed scripts)

| Script | Target Demographic | Model | Region |
|--------|-------------------|-------|--------|
| `seed.py` | Medanese Middle-Upper Class | `claude-haiku-4-5-20251001` | Medan, Indonesia |
| `seed_db.py` | Urban Millennial | `claude-haiku-4-5-20251001` | North America |

**Generation order (both scripts) — v3 pipeline:**
1. `generate_base_genome()` → gaussian(50,15) bell-curve + Big Five covariance (18 traits)
2. `apply_age_drift(genome, age)` → developmental personality maturation curves
3. `generate_cultural_profile(region, age)` → full cultural/religious profile
4. `apply_cultural_modifiers(genome, profile)` → adjusted genome with grounded literacy/friction
5. Build user prompt with cultural context block injected
6. Call Claude Haiku → JSONB life layers + voice_print + additional mutation events
7. Merge: `cultural_mutation_events` (Python) + `genome_mutation_log` (Claude)
8. Insert full payload with all 18 trait columns + cultural columns to Supabase

---

## Critical Environment Rules

- **Env file**: `pantheon.env` (NOT `.env`)
- **Always use**: `load_dotenv('pantheon.env', override=True)` — `override=True` is essential because `ANTHROPIC_API_KEY` is set as empty string at system level
- **Python**: `.venv/Scripts/python` (Windows)
- **Supabase key**: The key labeled `SUPABASE_SERVICE_ROLE_KEY` in `pantheon.env` is actually an **anon key** — works if RLS is off

---

## Key Files

| File | Purpose |
|------|---------|
| `main.py` | Modal orchestration — all 5 nodes + Node 6 presentation |
| `genome_culture.py` | **Cultural/religious engine** — ethnicity, religion, conversion, modifiers |
| `seed.py` | Genome builder (Haiku, Medanese Middle-Upper Class) |
| `seed_db.py` | Genome builder (Haiku, Urban Millennial North America) |
| `init_db.py` | Prints SQL for Supabase table creation (CREATE + ALTER migrations) |
| `check_db.py` | Counts agents in Supabase |
| `check_env.py` | Shows masked env variable values |
| `update_secrets.py` | Pushes `pantheon.env` → Modal secret `pantheon-secrets` |
| `test_claude.py` | Quick Claude API connectivity test |
| `final_test.py` | End-to-end Node 2 mock test (no Modal) |
| `dashboard.py` | Streamlit dashboard with 6 node cards + download buttons |

---

## Presentation Deck (Node 6)

- **Sentinel**: `PANTHEON_PPTX_FILE::<base_name>` in Node 5 output → dashboard shows 🎞️ download button
- **Design tokens**: Navy `1E2761`, Gold `E8B04B`, Ice Blue `CADCFC`, Dark BG `0D1B2A`, Calibri font
- **pptxgenjs**: installed at `D:/npm-global/node_modules/pptxgenjs`
- **PDF conversion**: not available — `.pptx` is final delivery format

---

## Adding a New Region / Demographic

To extend `genome_culture.py` with a new region (e.g. "Jakarta, Indonesia" or "Southeast Asia"):

1. Add an entry to `ETHNICITY_POOLS`
2. Add religion distributions to `RELIGION_BY_ETHNICITY` for each new ethnicity
3. Set an `INTERCULTURAL_MARRIAGE_PROB` entry for the region
4. Add `SOCIOECONOMIC_FRICTION_RANGES` and `LITERACY_RANGES` entries for each ethnicity
5. Optionally add culture-specific entries to `CULTURE_MODIFIERS`
6. Create a new seed script (copy `seed.py`, change `target_demographic` and `region`)
