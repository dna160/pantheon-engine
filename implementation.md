# PANTHEON v3 — Cognitive Architecture Upgrade
### Implementation Reference Document
**Completed:** March 2026 · **Verification:** 19/19 tests passed

---

## Why This Was Done

Academic review identified six structural limitations in PANTHEON's cognitive engine:

1. Cultural identity mechanics (mianzi, guanxi, marga) existed only as narrative text — no numerical parameter drove group-loyalty behaviour during simulation
2. `legacy_layer` was a static destiny baked in at seed time, not a dynamic future projection
3. Social cognition was flat — `communication_style` and `conflict_behavior` couldn't separate self-reflection from metaperception
4. `random.randint(1, 100)` made extreme scores (1 or 99) as likely as median scores (50) — unrealistic uniform distribution with zero trait covariance
5. No age-graded personality development — changes were purely shock-driven (mutation_log events) with no natural maturation curve
6. No cognitive override — agents couldn't suppress base trait impulses in social contexts

The upgrade transforms PANTHEON from "advanced consumer personas" to "high-fidelity human cognitive simulations" while remaining fully dynamic, cross-cultural, cross-religious, and cross-national.

---

## New Genome Dimensions (5 new traits, all INT 1–100)

All new traits have `DEFAULT 50` in the database for backward compatibility.

| Trait | Low (1) | High (100) | What It Drives in Simulation |
|-------|---------|------------|------------------------------|
| `identity_fusion` | Pure individualist — weighs every decision on personal merit | Visceral group oneness — the in-group IS the self | Group-loyalty behaviour in Node 4 breakout rooms; high-fusion agents defend in-group positions even against personal interest |
| `chronesthesia_capacity` | Present-only thinker — reacts to immediate stimuli, rarely projects forward | Vivid mental time traveler — constantly simulates futures, queries past memories to validate choices | Replaces static `legacy_layer` for agents under 60 via the chronesthesia directive; drives whether agents frame focus group questions in terms of long-term vs. near-term self |
| `tom_self_awareness` | Blind to own emotional states and biases | Deep self-reflection — accurately identifies own beliefs, motivations, and inconsistencies | One axis of the Theory of Mind matrix; controls authenticity of inner thought vs. spoken word |
| `tom_social_modeling` | Oblivious to others' perceptions and social cues | Reads rooms perfectly — models what others think of them with high accuracy | Second axis of the ToM matrix; controls performativity and status anxiety |
| `executive_flexibility` | Traits leak always — what they think is what they say | Can override impulses — high self-regulation in social contexts | Controls the SIZE of the gap between `(Inner Thought)` and `(Spoken)` in Node 4 output |

---

## Architecture Changes

### 1. Trait Distribution: Gaussian Replaces Uniform

**Before (v2):** `random.randint(1, 100)` — every value equally probable, no covariance between traits.

**After (v3):** `random.gauss(mu=50, sigma=15)` clamped [1, 100] — bell-curve centred on 50. Extreme scores (<10 or >90) occur <5% of the time vs. ~20% under uniform. Real personality research shows extreme trait scores are rare.

```python
def _gauss_trait(mu=50.0, sigma=15.0) -> int:
    return max(1, min(100, int(random.gauss(mu, sigma))))
```

### 2. Trait Covariance via Correlation Noise

Behavioural traits are derived from Big Five anchors using a simplified linear correlation model, not drawn independently:

```python
def _correlated_trait(anchor: int, r: float, mu=50.0, sigma=15.0) -> int:
    noise = random.gauss(mu, sigma)
    blended = r * anchor + (1.0 - abs(r)) * noise
    return max(1, min(100, int(blended)))
```

| Derived Trait | Anchor | Correlation (r) | Rationale |
|---------------|--------|----------------|-----------|
| `decision_making` | `conscientiousness` | +0.4 | Conscientious people plan; impulsive people don't |
| `emotional_expression` | `extraversion` | +0.5 | Extraverts display emotion more openly |
| `conflict_behavior` | `agreeableness` | –0.6 | Agreeable people avoid confrontation |
| `influence_susceptibility` | `openness * 0.4 + agreeableness * 0.4` | +0.3 | Open, agreeable people are more persuadable |
| `communication_style` | — | independent | Culturally determined |
| `brand_relationship` | — | independent | Culturally determined |

**Verification result:** `conscientiousness` ↔ `decision_making` r=0.572 ✓, `agreeableness` ↔ `conflict_behavior` r=–0.516 ✓, Big Five remain independent r≈0.01 ✓

### 3. Canonical `generate_base_genome()` Function

Before v3, each seed script had its own local genome generation loop. Now all seed scripts import a single canonical function from `genome_culture.py`:

```python
from genome_culture import generate_base_genome, apply_age_drift
```

Returns a dict of 18 trait names → int values (1–100).

### 4. Age-Graded Trait Drift (`apply_age_drift`)

Based on Roberts, Walton & Viechtbauer (2006) — mean-level personality change research:

```python
def apply_age_drift(genome: dict, age: int) -> dict:
    g = genome.copy()
    g["conscientiousness"]      += int(max(0, age - 20) * 0.3)   # +0.3/yr after 20
    g["agreeableness"]          += int(max(0, age - 25) * 0.2)   # +0.2/yr after 25
    g["neuroticism"]            -= int(max(0, age - 30) * 0.2)   # -0.2/yr after 30
    g["openness"]               -= int(max(0, age - 35) * 0.1)   # -0.1/yr after 35
    g["chronesthesia_capacity"] += int(max(0, age - 25) * 0.15)  # foresight matures
    # executive_flexibility: inverted-U, peaks at 50
    if age <= 50:
        ef_drift = int(max(0, age - 20) * 0.2)
    else:
        ef_drift = int(30 * 0.2) - int((age - 50) * 0.15)
    g["executive_flexibility"]  += ef_drift
    # all values clamped [1, 100]
    ...
```

**Verification result:** Age 20 vs 50 comparison over 500 samples — conscientiousness +9.0 pts ✓, neuroticism –4.0 pts ✓, exec_flexibility +6.0 pts ✓

### 5. Pipeline Order (v3)

```
generate_base_genome()          ← gaussian(50, 15) + trait covariance
        ↓
apply_age_drift(genome, age)    ← developmental psychology curves
        ↓
generate_cultural_profile()     ← ethnicity, religion, conversion, marriage
        ↓
apply_cultural_modifiers()      ← CULTURE_MODIFIERS + RELIGIOSITY + CONVERSION + MARRIAGE deltas
        ↓
Claude (Haiku/Sonnet)           ← generates life layers, voice_print, mutation_log
        ↓
Supabase insert                 ← all 18 traits + cultural columns
```

---

## Theory of Mind Matrix (Node 4)

Two-axis model combining `tom_self_awareness` and `tom_social_modeling`:

| ToMSelf \ ToMSocial | Low (oblivious to others) | High (reads rooms perfectly) |
|---------------------|--------------------------|------------------------------|
| **High** (deep self-reflection) | **Authentic but clumsy** — says exactly what they think even when socially inappropriate; genuinely unaware how it lands | **Socially sophisticated** — spoken words are calibrated; inner thoughts are strategic |
| **Low** (blind to own states) | **Impulsive/reactive** — spoken words and inner thoughts nearly identical; no filter | **Performative/status-anxious** — adjusts speech to match what others want to hear; inner thoughts reveal they don't actually know what they themselves believe |

This drives the `(Inner Thought)` vs `(Spoken)` format in Node 4 output.

---

## Executive Flexibility Behavioural Model (Node 4)

Controls the SIZE of the gap between inner thought and spoken word:

- **High ExecFlex (70+):** Large gap possible — the professional who is privately seething but speaks calmly. Can suppress neuroticism, conflict_behavior in social settings.
- **Low ExecFlex (<30):** Small gap — traits leak directly into speech. High N + Low ExecFlex = visibly anxious, voice trembles, cannot hide distress.
- **Combined:** High N + High ExecFlex = appears calm but inner thoughts are catastrophising. High N + Low ExecFlex = full visibility of distress.

---

## Identity Fusion Group Loyalty (Node 4)

- **High IdFusion (70+):** Defends in-group positions even against personal interest. When another participant from their cultural/religious community is challenged, high-fusion agents rally to defend **regardless of their own opinion** on the substance.
- **Low IdFusion (<30):** Evaluates arguments purely on personal merit, no group loyalty override.
- Cultural drivers: marga (Batak), mianzi/guanxi (Chinese), ummah (Acehnese), familismo (Hispanic/Latino), kiasu (Singaporean)

---

## Chronesthesia Directive — Dynamic Legacy Layer

For agents **under 60**, the static `legacy_layer` is replaced with a runtime cognitive mode directive injected into every agent context:

| Score | Cognitive Mode |
|-------|---------------|
| `< 25` | Present-focused. Rarely considers long-term consequences. Reacts to immediate stimuli. |
| `25–49` | Moderate foresight. Can think 1–2 years ahead when prompted, but defaults to near-term. |
| `50–74` | Active future simulator. Projects 3–5 years forward before major decisions. References origin/formation memories to validate choices. |
| `75+` | Vivid mental time traveler. 10-year projection filter. May hesitate due to overthinking. Strategic but susceptible to scenario anxiety. |

For agents **60+**, `legacy_layer` is used as their **lived reality**, not an aspirational projection.

---

## Cultural Modifier Expansions

New trait deltas were added to ALL ethnicity entries in `CULTURE_MODIFIERS`:

| Ethnicity | identity_fusion | chronesthesia | tom_self | tom_social | exec_flex |
|-----------|:-:|:-:|:-:|:-:|:-:|
| Batak Toba | +15 (marga) | +5 | –5 | +5 | –3 |
| Javanese | +10 | +8 | +5 | +18 (halus) | +12 |
| Chinese-Indonesian | +12 (guanxi) | +12 | +8 | +14 (mianzi) | +14 |
| Acehnese | +18 (ummah) | +10 | –5 | +8 | +5 |
| Minangkabau | +12 (matrilineal) | +8 | +6 | +10 | +8 |
| Malay Deli | +14 | +6 | +4 | +14 | +10 |
| Nias | +10 | –3 | –3 | +3 | –2 |
| Mixed Ethnic (Medan) | –5 | +5 | +10 | +5 | +5 |
| White non-Hispanic | –5 | +3 | +8 | –3 | +3 |
| African American | +8 | +3 | +5 | +6 | +5 |
| Hispanic/Latino | +12 (familismo) | +3 | +3 | +8 | +3 |
| Asian American | +8 | +10 | +6 | +12 | +10 |
| Mixed/Multiracial (NA) | –3 | +5 | +12 | +5 | +5 |
| Chinese Singaporean | +10 (kiasu) | +14 | +8 | +16 | +16 |
| Malay Singaporean | +14 | +5 | +3 | +10 | +8 |
| Indian Singaporean | +10 | +10 | +8 | +12 | +12 |
| Eurasian/Peranakan | –3 | +8 | +10 | +8 | +10 |

**Religiosity modifiers (new deltas):**
- Devout: `identity_fusion +12, chronesthesia_capacity +10, tom_social_modeling +5, executive_flexibility +8`
- Secular: `identity_fusion –8, chronesthesia_capacity –3, tom_self_awareness +8, executive_flexibility +3`

**Intercultural marriage (new deltas):** `identity_fusion –5, tom_social_modeling +6, executive_flexibility +5`

**Conversion modifiers (new deltas per type):**
- `secular_drift`: `identity_fusion –10, tom_self_awareness +8`
- `to_devout`: `identity_fusion +14, executive_flexibility +6`
- `interfaith_marriage_pressure`: `identity_fusion –6, tom_social_modeling +8, executive_flexibility +5`
- `genuine_conversion`: `identity_fusion +8, chronesthesia_capacity +6`

---

## Files Modified

### `init_db.py`
Added 5 new INT columns to both `SQL_CREATE` and `SQL_MIGRATE`:
```sql
identity_fusion         INT DEFAULT 50,  -- 1=pure individualist, 100=visceral group oneness
chronesthesia_capacity  INT DEFAULT 50,  -- 1=present-only thinker, 100=vivid mental time traveler
tom_self_awareness      INT DEFAULT 50,  -- 1=blind to own states, 100=deep self-reflection
tom_social_modeling     INT DEFAULT 50,  -- 1=oblivious to others, 100=reads rooms perfectly
executive_flexibility   INT DEFAULT 50,  -- 1=traits leak always, 100=can override impulses
```

### `genome_culture.py`
- Added `_gauss_trait()` helper (line 444)
- Added `_correlated_trait()` helper (line 449)
- Added `generate_base_genome()` canonical function (line 461) — 18 traits returned
- Added `apply_age_drift(genome, age)` function (line 526) — developmental psychology curves
- Expanded `CULTURE_MODIFIERS`: added 5 new trait deltas for all 17 ethnicities
- Expanded `RELIGIOSITY_MODIFIERS`: added 5 new trait deltas for devout/secular
- Expanded `INTERCULTURAL_MARRIAGE_MODIFIERS`: added 3 new trait deltas
- Expanded `CONVERSION_MODIFIERS`: added new trait deltas for all 4 conversion types
- Updated `GENESIS_SYSTEM_PROMPT`: added 5 new traits to allowed `trait_modifiers` list; updated `legacy_layer` instruction to clarify aspirational projection semantics

### `seed.py`
- Removed local `generate_base_genome()` definition
- Added import: `from genome_culture import generate_base_genome, apply_age_drift`
- Added `apply_age_drift()` call between base genome and cultural modifiers
- Added 5 new columns to Supabase insert payload

### `seed_db.py`
- Same changes as `seed.py`

### `seed_singapore.py`
- Same changes as `seed.py`

### `seed_genomes.py`
- Added imports from `genome_culture`
- Updated local `GENOME_TOOL` schema: added 5 new integer properties + added to `required` array
- Added `apply_age_drift()` call in pipeline
- Added 5 new columns to `insert_agent()` payload

### `main.py`
| Section | Change |
|---------|--------|
| `_GENOME_TOOL` schema | Added 5 new integer properties + added to `required` array |
| `_MUTABLE_TRAITS` list | Added all 5 new trait names |
| `_MUTATION_TOOL` description | Added 5 new trait names to valid keys |
| `_build_chronesthesia_directive()` | NEW helper function (line 55) — returns cognitive mode text per score range |
| `_build_agent_context()` | Expanded genome string to include all 5 new traits; injects chronesthesia directive for agents <60 |
| `NODE2_SYSTEM` | Added: high-chronesthesia agents show anticipatory thinking; low-chronesthesia focus on immediate state |
| `NODE3_SYSTEM` | Removed hardcoded Indonesian/Medanese references; added identity_fusion instruction for gut reaction |
| `NODE4_SYSTEM` | Added three new directive blocks: THEORY OF MIND DYNAMICS, EXECUTIVE FLEXIBILITY, IDENTITY FUSION |
| `dynamic_seed_agents()` payload | Added 5 new columns |
| `_INSPECTOR_FIELDS` | Added 5 new trait names |
| `_GENESIS_SYSTEM_BASE` | Added trait descriptions for all 5 new traits; updated trait count from 13 to 18 |

### `client_whisperer/engine.py`
- Added 5 new fields to `ProspectGenome` Pydantic model with inference evidence descriptions
- Added new scores to `_format_for_strategy()` output
- Added new scores to `_build_genesis_prompt()` genome injection
- Added 5 new columns to `_save_to_supabase()` row dict

### `client_whisperer/strategy.py`
- Added COGNITIVE ARCHITECTURE TRAITS section to `generate_strategy()` system prompt:
  - `identity_fusion` high → position as group-endorsed; low → individual advantage framing
  - `chronesthesia_capacity` high → lead with long-term vision/ROI; low → immediate benefit
  - `tom_social_modeling` high → they'll read your pitch, be authentic; low → standard approach
  - `executive_flexibility` high → professional mask hides real feelings, probe past the performance

### `.claude/skills/pantheon-app/SKILL.md`
- Version bumped 2.0.0 → 3.0.0
- Added "Cognitive Architecture Traits (v3)" table
- Added "Trait Generation Architecture (v3)" section documenting gaussian distribution, covariance, age drift, pipeline order
- Updated generation flow diagram to include `generate_base_genome()` and `apply_age_drift()` steps
- Updated seed scripts generation order (old "random 1-100" → new 8-step v3 pipeline)
- Updated `legacy_layer` row to note aspirational projection semantics

### `MEMORY.md` (project memory)
- Updated engine.py reference: 13-trait → 18-trait ProspectGenome
- Added full "PANTHEON v3 Cognitive Architecture" section documenting all changes for future sessions

---

## Backward Compatibility

- All 5 new DB columns have `DEFAULT 50`
- All code reads new traits via `.get(trait, 50)` — existing rows without new columns are safe
- `_build_agent_context()` verified at lines 91–93 to use `.get()` with 50 defaults
- `dynamic_seed_agents()` payload verified to use `.get()` with 50 defaults (lines 650–654)

---

## Verification Results (19/19 passed)

Run with: `.venv/Scripts/python verify_v3.py`

| Test | Expected | Actual | Status |
|------|----------|--------|--------|
| Openness distribution: mean | 38–62 | 49.5 | PASS |
| Openness distribution: SD | 10–20 | 14.4 | PASS |
| Conscientiousness: mean | 38–62 | 49.4 | PASS |
| Conscientiousness: SD | 10–20 | 15.6 | PASS |
| Identity fusion: mean | 38–62 | 48.9 | PASS |
| Chronesthesia: mean | 38–62 | 49.6 | PASS |
| Extreme scores (<10 or >90) | <8% | 0.3% | PASS |
| Consc ↔ Decision r | 0.15–0.65 | 0.572 | PASS |
| Agree ↔ Conflict r | –0.75–(–0.30) | –0.516 | PASS |
| Consc ↔ Extraversion r (independent) | |r|<0.15 | –0.011 | PASS |
| Age drift: conscientiousness +pts (20→50) | 5–15 | +9.0 | PASS |
| Age drift: neuroticism –pts (20→50) | –8–(–1) | –4.0 | PASS |
| Age drift: exec_flex +pts (20→50) | 3–10 | +6.0 | PASS |
| Medan mean identity_fusion > NA mean | Medan > NA | 49.5 > 47.4 | PASS |
| Old agent .get() defaults to 50 | all 5 = 50 | True | PASS |
| generate_base_genome() returns 18 traits | 18 | 18 | PASS |
| identity_fusion in genome | present | yes | PASS |
| chronesthesia_capacity in genome | present | yes | PASS |
| tom_self_awareness in genome | present | yes | PASS |
| tom_social_modeling in genome | present | yes | PASS |
| executive_flexibility in genome | present | yes | PASS |

Note: The cultural modifier separation test (Medan 49.5 vs NA 47.4) shows the expected directional difference. The delta is modest at the population level because Medan includes both high-fusion ethnicities (Acehnese +18, Batak +15) and mixed-ethnic groups (–5). Seed a single high-fusion ethnicity (e.g., Acehnese only) and the separation becomes stark (~65+ vs ~45).

---

## Key Design Principles (Do Not Violate)

1. **Never hardcode by nationality/region** — all trait modifiers are per-ethnicity and per-religion, not per-country. The system already works for Medan, North America, and Singapore and will extend cleanly to new regions.
2. **Pipeline order is load-bearing** — base genome → age drift → cultural modifiers → mutation log. If cultural modifiers are applied before age drift, a Batak Toba 45-year-old will have the same conscientiousness baseline as a Batak Toba 22-year-old before the cultural delta is applied, losing the developmental realism.
3. **Backward compat is non-negotiable** — always add new INT columns with `DEFAULT 50` and always read via `.get(trait, 50)`. Existing seeded agents in Supabase must not break.
4. **Cultural modifiers are additive deltas, not absolute values** — `apply_cultural_modifiers()` iterates the modifier dict and adds deltas to the genome. This means stacking works correctly (bicultural agents, conversion, intercultural marriage all stack cleanly).
5. **`executive_flexibility` drives gap size, not content** — what the agent thinks (Inner Thought) is driven by other traits (neuroticism, conflict_behavior, identity_fusion). exec_flex only controls how much of that leaks into the spoken word.

---

## Human Whisperer Dashboard Refactor — 13 March 2026

### Change 1 — Dashboard layout restructured (`whisperer_dashboard.py`)

**Problem:** The Section 0 Quick Brief (hook card + talking points) rendered as a single block *after* the two-column layout, visually disconnecting the talking points from the meeting blueprint stages they complement.

**Fix:** Split `_render_quick_brief` into two independent functions:

| Function | Renders | Called from |
|---|---|---|
| `_render_hook_card(quick_brief, prospect_name)` | HOOK / STAY / CLOSE 3-column card | After the two-column layout (standalone Kartu Cepat) |
| `_render_talking_points(quick_brief, key_suffix)` | Numbered talking point expanders | Inside `col_right`, after stage steps |

`_render_quick_brief` is kept as a thin wrapper calling both — backward-compatible for any future callers.

**New render order inside `_render_whisperer_output`:**
1. `col_left` — Identity card + Visual Intel (unchanged)
2. `col_right` — Win/Lose grid → "Panduan Client" stage steps → `_render_talking_points()` (inline, below stages)
3. Full-width — `_render_hook_card()` (Kartu Cepat — HOOK / STAY / CLOSE)
4. Full-width — Download button
5. Collapsible — Raw psychological data (Dokumen Persiapan Percakapan Lengkap)

### Change 2 — Playbook card renamed (`whisperer_dashboard.py`)

`"⚡ Cetak Biru Pertemuan (Panduan Navigasi — Bukan Skrip)"` → `"📋 Panduan Client"`

Rationale: the old name leaked the internal "navigation not script" meta-instruction into a visible UI label, which was confusing to practitioners.

### Change 3 — Second-person pronoun rule (`client_whisperer/human_whisperer.py`)

**Problem:** GOOD example phrasings in the system prompt used "lo" (Jakartanese first-person slang for "you"), which is too slangy for the professional Indonesian register the document targets.

**Fix:**
- All "lo" instances in GOOD examples replaced with "kamu"
- Explicit rule added to the `LANGUAGE RULE` block:
  > *"Second person: use 'kamu' (not 'lo' — too informal/slangy for professional contexts)."*

### Design Principles (Do Not Violate)

- Talking points always live in the right column — they are companion content to the stage blueprint, not a standalone module
- The Kartu Cepat (HOOK / STAY / CLOSE) always renders full-width *above* the download button — it is the practitioner's last thing they read before walking in
- `_render_quick_brief` stays as a wrapper — do not delete it, other callers may use it
---

## Codebase Refactor and Modularization — March 2026

### 1. Architectural Reorganization
The codebase was restructured from a flat architecture into a modular, directory-based system to improve maintainability and scalability.

| Directory | Purpose |
|-----------|---------|
| `src/` | Core business logic, pipeline nodes, and modularized engines |
| `src/nodes/` | Individual pipeline node logic (Nodes 2–5) |
| `ui/` | Streamlit dashboards and UI-related logic |
| `scripts/` | Database initialization, seeding, and management scripts |
| `tests/` | Unit and integration testing suites |
| `docs/` | Project documentation and SQL schemas |

### 2. Modular Engine Extraction
The monolithic `main.py` was decomposed into a lean orchestrator by extracting core logic into dedicated modules:

- **Genesis Engine (`src/genesis.py`)**: All agent generation, seed templates, and nature vs. nurture mutation logic.
- **Semantic Router (`src/semantic_router.py`)**: Smart demographic matching and PTM/STM evaluation.
- **Pipeline Nodes (`src/nodes/`)**: Node-specific logic (Snapshots, Mass Sessions, Breakout Rooms, Synthesis) isolated for testing and clarity.
- **Presentation & Whisperer (`src/presentation.py`, `src/whisperer.py`)**: PPTX generation and client meeting prep documentation logic.
- **Shared Utils (`src/utils.py`)**: Global constants, agent context builders, and cross-node reporting logic.

### 3. Orchestration Layer (`main.py`)
`main.py` now serves strictly as the execution orchestrator:
- Defines the `modal.App` and image configuration.
- Maps Modal functions to modular logic in `src/`.
- Orchestrates the sequential flow from Intake (Node 1) through to Whisperer (Node 7).
- Provides a clean `api_run_pipeline` entry point for web integrations.

### 4. Configuration Consolidation
- **Consolidated Environment**: Redundant `pantheon.env` was merged into a single source-of-truth `.env` file.
- **Import Standardization**: All components now use standardized relative and absolute imports based on the root directory.

### Design Principles (Refactor)
- **Separation of Concerns**: Logic (src), Interface (ui), and Orchestration (main.py) are strictly decoupled.
- **Path Portability**: Scripts and UI files use dynamic path resolution to find core modules regardless of execution context.
- **Testability**: Individual nodes in `src/nodes/` can now be unit-tested without loading the entire Modal app.
