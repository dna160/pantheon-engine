# CLAUDE.md — Pantheon 2.0 Harness Instructions
**For Claude Code. Read this entire file before writing a single line of code.**  
**Version:** 2.0.0 | **Updated:** April 2026

---

## WHAT YOU ARE BUILDING

Pantheon 2.0 is a live conversation assistance system. It reads audio from a Plaud Note Pro device during a B2B sales/advisory conversation, classifies the psychological moment type in real time, and surfaces guidance to the practitioner via a smartwatch or phone HUD — all in under 400ms, with zero cloud API calls mid-session.

The system runs on three distinct execution zones. The harness (this file's orchestration logic) owns Zones 1 and 3. Zone 2 is inference-free.

**Primary outcome metrics:** Hook Rate (attention activation) and Closing Rate (decision conversion).

---

## MANDATORY FIRST STEPS

Before writing any code, run this sequence:

```bash
# 1. Read the PRD
cat PRD_Pantheon_2.0.md

# 2. Read all agent skill files
cat skills/harness-orchestrator/SKILL.md
cat skills/adversarial-psychologist/SKILL.md

# 3. Verify the file tree matches what's in FILE_TREE.md
cat FILE_TREE.md

# 4. Check existing Pantheon codebase conventions
# (genome_culture.py, seed_genomes.py patterns — do not break these)
```

Do not start coding until you have read all four documents.

---

## HARNESS WORKFLOW LOOP

This is the core loop Claude Code must implement. Every module maps to a step in this loop.

```
┌──────────────────────────────────────────────────┐
│              ZONE 1: PRE-SESSION                  │
│                                                   │
│  1. genome_resolver.py                            │
│     → Check Supabase for existing genome          │
│     → If missing/stale: run scrape_pipeline       │
│     → If scrape fails: launch intake_form         │
│     → Output: GenomeBundle{genome, confidence}    │
│                                                   │
│  2. rwi_calculator.py                             │
│     → Compute RWI from GenomeBundle               │
│     → Output: RWISnapshot{score, components}      │
│                                                   │
│  3. psych_review_agent.py  [ADVERSARIAL]          │
│     → Validate genome predictions                 │
│     → Flag ecological validity issues             │
│     → Output: PsychReviewReport{flags, warnings}  │
│                                                   │
│  4. cache_builder.py  [HARNESS LLM CALL]          │
│     → Send genome + RWI to configured LLM         │
│     → Receive 6×3 dialog option tree              │
│     → Write to local cache file                   │
│     → Output: DialogCache{18 options + probs}     │
│                                                   │
│  5. slm_warmer.py                                 │
│     → Load local SLM into memory                  │
│     → Run warm-up inference (dummy input)         │
│     → Confirm <250ms cold inference latency       │
│                                                   │
│  6. session_init.py                               │
│     → Display pre-session screen on phone         │
│     → Show: genome confidence, RWI score,         │
│       psych review flags, ready confirmation      │
│     → Wait for practitioner GO signal             │
└──────────────────┬───────────────────────────────┘
                   │ Practitioner confirms GO
                   ▼
┌──────────────────────────────────────────────────┐
│              ZONE 2: LIVE SESSION                 │
│       (NO CLOUD LLM. NO NETWORK. LOCAL ONLY.)     │
│                                                   │
│  TWO PARALLEL STREAMS run simultaneously:         │
│                                                   │
│  STREAM A — TRANSCRIPT (verbal)                   │
│  audio_bridge → transcription_engine              │
│    → moment_classifier                            │
│    → verbal Observed State fields                 │
│                                                   │
│  STREAM B — PARALINGUISTICS (how it's said)       │
│  audio_bridge → audio_signal_processor            │
│    → paralinguistic_extractor                     │
│    → speech_rate / volume / pause /               │
│      voice_tension / cadence fields               │
│    → divergence_detector                          │
│      (fires DivergenceAlert if A ≠ B)             │
│                                                   │
│  BOTH STREAMS FEED:                               │
│                 ↓                                 │
│  bar_calculator.py                                │
│  → Update Hook bar (0–100)                        │
│  → Update Close bar (0–100)                       │
│  → Both streams contribute                        │
│                 ↓                                 │
│  dialog_selector.py                               │
│  → Retrieve cache[moment_type] foundations        │
│                 ↓                                 │
│  slm_adapter.py  ← THE LIVE INTELLIGENCE LAYER   │
│  → Input: cache foundations + full Observed State │
│  → Output: adapted framing per option             │
│  → Budget: <200ms. Hard limit: 350ms.             │
│  → Hard fallback: base cache unmodified           │
│                 ↓                                 │
│  display_driver.py  [HARDWARE ABSTRACTION]        │
│  → WatchDriver: bars + 3-word trigger + haptic    │
│  → PhoneDriver: full HUD + HiddenSignalPanel      │
│  → GlassesDriver: stub (v2)                       │
│                 ↓                                 │
│  session_logger.py                                │
│  → Write event every 30s                          │
│  → Write on moment type change                    │
│  → Write paralinguistic snapshot every 30s        │
│  → Write on practitioner option choice            │
└──────────────────┬───────────────────────────────┘
                   │ Session ends
                   ▼
┌──────────────────────────────────────────────────┐
│              ZONE 3: POST-SESSION                 │
│                                                   │
│  1. session_analyzer.py  [HARNESS LLM CALL]       │
│     → Parse session_log                           │
│     → Surface mutation candidates                 │
│     → Compute practitioner genome deltas          │
│                                                   │
│  2. mutation_review_screen.py                     │
│     → Present candidates to practitioner          │
│     → Human confirms or dismisses each            │
│     → GATE: no automatic genome writes            │
│                                                   │
│  3. genome_writer.py                              │
│     → Write confirmed mutations to Supabase       │
│     → Log to mutation_log with timestamp          │
│     → Enforce velocity gate (21 days, 3+ obs)     │
│                                                   │
│  4. practitioner_profile_updater.py               │
│     → Update practitioner genome from session     │
│     → Generate Mirror Report (4 observations)     │
│                                                   │
│  5. mirror_report_renderer.py                     │
│     → Display Mirror Report to practitioner       │
│     → Never shown on live HUD — post-session only │
└──────────────────────────────────────────────────┘
```

---

## FILE TREE (Canonical — Do Not Deviate)

```
pantheon2/
├── CLAUDE.md                          ← This file
├── PRD_Pantheon_2.0.md                ← Product requirements
├── FILE_TREE.md                       ← This tree (machine-readable)
├── harness.config.json                ← LLM provider config (Zone 1/3)
├── .env.example                       ← Environment variable template
│
├── skills/                            ← Agent skill definitions
│   ├── harness-orchestrator/
│   │   ├── SKILL.md
│   │   └── prompts/
│   │       ├── zone1_cache_builder.txt
│   │       └── zone3_session_analyzer.txt
│   └── adversarial-psychologist/
│       ├── SKILL.md
│       └── prompts/
│           ├── validity_review.txt
│           └── ecological_validity_review.txt
│
├── backend/                           ← FastAPI Python backend
│   ├── main.py                        ← FastAPI app entry point
│   ├── requirements.txt
│   │
│   ├── harness/                       ← Zone 1 and 3 orchestration
│   │   ├── __init__.py
│   │   ├── harness_runner.py          ← Main harness entry point
│   │   ├── llm_client.py              ← Provider-agnostic LLM client
│   │   ├── harness_config.py          ← Config loader
│   │   └── providers/
│   │       ├── anthropic_provider.py
│   │       ├── openai_provider.py
│   │       ├── gemini_provider.py
│   │       └── lmstudio_provider.py
│   │
│   ├── genome/                        ← Genome management
│   │   ├── __init__.py
│   │   ├── genome_resolver.py         ← Priority chain: Supabase → scrape → intake
│   │   ├── genome_builder.py          ← Builds genome from raw signals
│   │   ├── genome_writer.py           ← Mutation-gated writes to Supabase
│   │   ├── parameter_definitions.py   ← All 18 parameters with derivation logic
│   │   ├── confidence_scorer.py       ← HIGH/MEDIUM/LOW confidence rating
│   │   └── scrape_pipeline/
│   │       ├── __init__.py
│   │       ├── linkedin_scraper.py
│   │       ├── instagram_scraper.py
│   │       └── signal_extractor.py
│   │
│   ├── session/                       ← Zone 2 live session engine
│   │   ├── __init__.py
│   │   ├── session_init.py            ← Pre-session setup + practitioner GO screen
│   │   ├── session_runner.py          ← Main Zone 2 event loop
│   │   ├── session_logger.py          ← 30s snapshots + event writes
│   │   └── session_analyzer.py        ← Zone 3: post-session log analysis
│   │
│   ├── audio/                         ← Audio processing
│   │   ├── __init__.py
│   │   ├── audio_bridge.py            ← BLE receiver from Plaud Note Pro
│   │   ├── transcription_engine.py    ← Local transcription (Whisper small)
│   │   └── audio_buffer.py            ← 50ms chunk buffering
│   │
│   ├── classifier/                    ← Moment classification
│   │   ├── __init__.py
│   │   ├── moment_classifier.py       ← 6-type classifier dispatcher
│   │   ├── local_classifier.py        ← Pre-trained lightweight classifier
│   │   └── slm_classifier.py          ← Local SLM fallback classifier
│   │
│   ├── slm/                           ← Local SLM management
│   │   ├── __init__.py
│   │   ├── slm_warmer.py              ← Pre-session model load + warm-up
│   │   ├── slm_runner.py              ← Inference runner with 350ms timeout
│   │   └── slm_config.py             ← Model path, quantization settings
│   │
│   ├── rwi/                           ← Receptivity Window Index
│   │   ├── __init__.py
│   │   └── rwi_calculator.py         ← RWI compute from genome
│   │
│   ├── bars/                          ← Hook/Close bar engine
│   │   ├── __init__.py
│   │   └── bar_calculator.py         ← Bar update logic + genome modifiers
│   │
│   ├── dialog/                        ← Dialog option management
│   │   ├── __init__.py
│   │   ├── cache_builder.py           ← Zone 1: LLM call → 18-option cache
│   │   ├── dialog_selector.py         ← Cache lookup + SLM fallback
│   │   └── probability_engine.py      ← Probability compression rules
│   │
│   ├── display/                       ← HUD rendering (hardware abstraction)
│   │   ├── __init__.py
│   │   ├── display_driver.py          ← Abstract base DisplayDriver
│   │   ├── watch_driver.py            ← Smartwatch: bars + 3-word + haptic
│   │   ├── phone_driver.py            ← Phone landscape: full HUD
│   │   └── glasses_driver.py          ← Stub (v2)
│   │
│   ├── practitioner/                  ← Practitioner self-profile
│   │   ├── __init__.py
│   │   ├── practitioner_profile.py    ← Parameter definitions + accumulation
│   │   ├── practitioner_updater.py    ← Update from session log
│   │   └── mirror_report.py           ← 4-observation post-session report
│   │
│   ├── psych_review/                  ← Adversarial psychology agent
│   │   ├── __init__.py
│   │   ├── psych_review_agent.py      ← Main adversarial agent runner
│   │   ├── validity_checker.py        ← Genome prediction validity checks
│   │   └── ecological_validator.py    ← Indonesian B2B context checks
│   │
│   └── db/                            ← Database layer
│       ├── __init__.py
│       ├── supabase_client.py         ← Supabase connection
│       ├── genome_repo.py             ← Genome read/write operations
│       └── session_repo.py            ← Session log storage
│
├── mobile/                            ← React Native mobile app
│   ├── package.json
│   ├── app.json
│   ├── index.js
│   │
│   ├── src/
│   │   ├── App.tsx
│   │   ├── navigation/
│   │   │   └── RootNavigator.tsx
│   │   │
│   │   ├── screens/
│   │   │   ├── PreSessionScreen.tsx   ← Genome confidence, RWI, GO button
│   │   │   ├── LiveHUDScreen.tsx      ← Full phone HUD (landscape)
│   │   │   ├── MutationReviewScreen.tsx ← Post-session: confirm/dismiss
│   │   │   └── MirrorReportScreen.tsx  ← Post-session: 4 observations
│   │   │
│   │   ├── components/
│   │   │   ├── HookCloseBar.tsx       ← Hook/Close bar visualization
│   │   │   ├── DialogOptions.tsx      ← 3 options with probability bars
│   │   │   ├── RWIIndicator.tsx       ← RWI score + window status
│   │   │   ├── ConfidenceBadge.tsx    ← HIGH/MEDIUM/LOW genome confidence
│   │   │   ├── PsychWarningCard.tsx   ← Adversarial review flags
│   │   │   └── MomentTypeLabel.tsx    ← Current moment type display
│   │   │
│   │   ├── ble/
│   │   │   ├── BLEManager.ts          ← Plaud Note BLE connection
│   │   │   └── AudioStreamer.ts        ← BLE audio → backend pipe
│   │   │
│   │   ├── watch/
│   │   │   └── WatchBridge.ts         ← React Native → WatchOS/WearOS bridge
│   │   │
│   │   ├── services/
│   │   │   ├── SessionService.ts      ← Backend API client
│   │   │   └── HUDStateManager.ts     ← Local HUD state (no API calls live)
│   │   │
│   │   └── types/
│   │       └── index.ts               ← Shared TypeScript types
│   │
│   └── __tests__/
│
└── tests/
    ├── unit/
    │   ├── test_genome_resolver.py
    │   ├── test_rwi_calculator.py
    │   ├── test_moment_classifier.py
    │   ├── test_bar_calculator.py
    │   ├── test_dialog_selector.py
    │   └── test_probability_engine.py
    ├── integration/
    │   ├── test_zone1_pipeline.py
    │   ├── test_zone2_loop.py
    │   └── test_zone3_pipeline.py
    └── latency/
        └── test_zone2_latency.py      ← Must pass <400ms p95
```

---

## CODING STANDARDS

### Python
- Python 3.11+
- FastAPI for all API endpoints
- Pydantic v2 for all data models
- Type annotations on every function signature
- No implicit state — every function takes explicit inputs and returns explicit outputs
- `async/await` everywhere in Zone 2 (latency critical)
- No global mutable state in Zone 2 modules

### React Native
- TypeScript strict mode
- Functional components only
- No class components
- State management: Zustand (lightweight, no Redux)
- BLE library: `react-native-ble-plx`
- Watch bridge: `react-native-watch-connectivity`

### Module Contracts
Every module must have a docstring that specifies:
```python
"""
Module: genome_resolver.py
Zone: 1 (Pre-session)
Input: ProspectID (str), HarnessConfig
Output: GenomeBundle (genome: dict, confidence: ConfidenceLevel)
LLM calls: 0 (this module does not call LLMs — it calls the scrape pipeline)
Side effects: May write to Supabase if fresh scrape completes
Latency tolerance: 3–8 minutes
"""
```

### The Mutation Gate — NEVER BYPASS
```python
# This check must appear in genome_writer.py
# It is not optional. It is not configurable. It cannot be removed.

def validate_mutation_gate(
    observations: list[Observation],
    trait_name: str,
    current_genome: Genome
) -> MutationDecision:
    """
    Returns APPROVED only if:
    - 3+ independent observations
    - 2+ separate contexts
    - 21+ day span
    - 1+ cold-context signal
    """
```

---

## HARNESS CONFIGURATION

`harness.config.json` (in project root — never commit API keys):

```json
{
  "zone1": {
    "provider": "anthropic",
    "model": "claude-sonnet-4-20250514",
    "max_tokens": 2000,
    "temperature": 0.3
  },
  "zone2": {
    "slm_model_path": "./models/phi-3-mini-4k-instruct-q4_k_m.gguf",
    "slm_max_tokens": 150,
    "slm_timeout_ms": 350,
    "fallback_to_cache": true
  },
  "zone3": {
    "provider": "anthropic",
    "model": "claude-sonnet-4-20250514",
    "max_tokens": 3000,
    "temperature": 0.4
  }
}
```

**To swap LLMs:** Edit `harness.config.json` only. No code changes required.  
**Supported providers:** `anthropic`, `openai`, `gemini`, `lmstudio`  
**LM Studio:** Set `provider: "lmstudio"` and `model: "http://localhost:1234/v1"` — the lmstudio_provider uses the OpenAI-compatible endpoint.

---

## ENVIRONMENT VARIABLES

```bash
# Copy .env.example → .env and fill in:
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
ANTHROPIC_API_KEY=        # Zone 1/3 default
OPENAI_API_KEY=            # Optional, if using openai provider
GEMINI_API_KEY=            # Optional, if using gemini provider
PLAUD_BLE_DEVICE_ID=       # BLE device identifier for Plaud Note Pro
SLM_MODEL_PATH=            # Absolute path to local GGUF/ONNX model file
```

---

## CRITICAL CONSTRAINTS — READ BEFORE EVERY BUILD SESSION

1. **Zone 2 never calls any external API.** If you find yourself writing an API call inside `session_runner.py` or any module in `audio/`, `classifier/`, `bars/`, `dialog/`, or `display/`, stop. That code is wrong.

2. **The mutation gate is inviolable.** `genome_writer.py` must check all gate conditions before writing. There is no override path. There is no admin bypass. This is a product integrity requirement.

3. **The DisplayDriver is an abstraction.** All HUD rendering calls go through `DisplayDriver`. Direct calls to watch or phone hardware APIs live only inside `WatchDriver` and `PhoneDriver`. `GlassesDriver` is a stub that logs calls without rendering.

4. **Genome confidence is always shown.** The `ConfidenceBadge` component must appear on every screen that displays genome-derived recommendations. It is never optional.

5. **Adversarial psych review flags are always shown pre-session.** If `PsychReviewReport` contains `HIGH` severity flags, the practitioner must acknowledge them before pressing GO. The session cannot start until acknowledgment is received.

6. **Mirror Report is post-session only.** Nothing from `mirror_report.py` appears on the live HUD. This is hardcoded — not configurable.

---

## CONTEXT WINDOW MANAGEMENT FOR CLAUDE CODE

This project is large. To avoid context overflow between sessions, follow this protocol:

**At the start of every new Claude Code session:**
```
1. Read CLAUDE.md (this file)
2. Read FILE_TREE.md
3. Read the specific module you are about to work on
4. Read its direct dependencies
5. Do NOT read the entire codebase
```

**When finishing a Claude Code session:**
```
1. Write a HANDOFF.md in the module directory you were working in
2. Format:
   - What is done
   - What is next
   - What decisions were made and why
   - Any open issues
3. Update FILE_TREE.md if new files were created
```

**Module build order (do not skip ahead):**
```
Phase 1: Foundation
  db/ → genome/ → rwi/ → harness/

Phase 2: Zone 1 Pipeline
  psych_review/ → dialog/cache_builder → session/session_init

Phase 3: Zone 2 Engine
  audio/ → classifier/ → slm/ → bars/ → dialog/dialog_selector → display/

Phase 4: Zone 3 Pipeline
  session/session_analyzer → practitioner/ → session/mutation_review

Phase 5: Mobile App
  mobile/ble/ → mobile/screens/PreSession → mobile/screens/LiveHUD
  → mobile/screens/MutationReview → mobile/screens/MirrorReport

Phase 6: Tests
  unit/ → integration/ → latency/
```

Build one phase completely before starting the next. Each phase ends with passing tests.

---

*End of CLAUDE.md*
