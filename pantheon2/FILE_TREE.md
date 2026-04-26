# FILE_TREE.md — Pantheon 2.0 Project Structure
**Machine-readable reference for Claude Code context management.**
**Update this file whenever you create, rename, or delete a module.**

---

## BUILD STATUS

| Phase | Modules | Status |
|-------|---------|--------|
| Phase 1: Foundation | db/, genome/, rwi/, harness/ | ✅ Complete — 33/33 tests passing |
| Phase 2: Zone 1 Pipeline | psych_review/, dialog/cache_builder, session/session_init | ✅ Complete — 60/60 tests passing |
| Phase 3: Zone 2 Engine | audio/, classifier/, slm/, bars/, dialog/dialog_selector, display/ | ✅ Complete — 97/97 tests passing |
| Phase 4: Zone 3 Pipeline | session/session_analyzer, practitioner/, mutation_review | ✅ Complete — 122/122 tests passing |
| Phase 5: Mobile App | mobile/ble/, mobile/screens/, mobile/components/ | ✅ Complete — all files written |
| Phase 6: Tests | unit/, integration/, latency/ | ✅ Complete — 154/154 tests passing |

---

## COMPLETE FILE TREE

```
pantheon2/
│
├── CLAUDE.md                          [SEED] Harness instructions for Claude Code
├── PRD_Pantheon_2.0.md                [SEED] Product requirements document
├── FILE_TREE.md                       [SEED] This file — updated each phase
├── HANDOFF_phase2.md                  [✅ Phase 2] Phase 2 handoff
├── HANDOFF_phase3.md                  [✅ Phase 3] Phase 3 handoff
├── HANDOFF_phase4.md                  [✅ Phase 4] Phase 4 handoff
├── mobile/HANDOFF_phase5.md           [✅ Phase 5] Phase 5 handoff — read before Phase 6
├── harness.config.json                [SEED] LLM provider config
├── .env.example                       [SEED] Environment variable template
│
├── skills/
│   ├── harness-orchestrator/
│   │   ├── SKILL.md                   [SEED] Zone 1/3 orchestration spec
│   │   └── prompts/
│   │       ├── zone1_cache_builder.txt        [✅ Phase 2] Full cache builder prompt
│   │       └── zone3_session_analyzer.txt     [✅ Phase 2] Full session analyzer prompt
│   └── adversarial-psychologist/
│       ├── SKILL.md                   [SEED] Psych review agent spec
│       └── prompts/
│           ├── validity_review.txt            [✅ Phase 2] Full validity review prompt
│           └── ecological_validity_review.txt [✅ Phase 2] Full ecological review prompt
│
├── db/
│   └── schema_v2.sql                  [✅ Phase 1] 6 new tables; v1 agent_genomes untouched
│
├── backend/
│   ├── main.py                        [✅ Pre-Phase 6 fix] FastAPI: /health, /session/prepare (rich), /session/close, /session/{id}/analysis, /session/{id}/mutation/confirm, /session/start, /session/{id}/end, /session/acknowledge_flag, /session/{id}/mirror_report, /session/{id}/mutation/respond, ws/hud/{id}, ws/audio/{id}
│   ├── requirements.txt               [✅ Phase 1]
│   │
│   ├── harness/
│   │   ├── __init__.py                [✅ Phase 1]
│   │   ├── harness_runner.py          [✅ Phase 1] Zone 1+3 orchestration; asyncio.gather for parallel steps
│   │   ├── llm_client.py              [✅ Phase 1] Provider-agnostic factory
│   │   ├── harness_config.py          [✅ Phase 1] JSON loader; PsychReviewConfig included
│   │   └── providers/
│   │       ├── anthropic_provider.py  [✅ Phase 1] Async + prompt caching (cache_control: ephemeral)
│   │       ├── openai_provider.py     [✅ Phase 1] Async
│   │       ├── gemini_provider.py     [✅ Phase 1] Sync wrapped in asyncio executor
│   │       └── lmstudio_provider.py   [✅ Phase 1] OpenAI-compat, no API key
│   │
│   ├── genome/
│   │   ├── __init__.py                [✅ Phase 1]
│   │   ├── genome_resolver.py         [✅ Phase 1] Priority: Supabase → scrape → intake; never raises
│   │   ├── genome_builder.py          [✅ Phase 1] Rule-based 18-param derivation; optional v1 culture import
│   │   ├── genome_writer.py           [✅ Phase 1] MUTATION GATE — hardcoded, no bypass
│   │   ├── parameter_definitions.py   [✅ Phase 1] All 18 params + ObservedState + DeltaSignal + RWI + GenomeBundle
│   │   ├── confidence_scorer.py       [✅ Phase 1] HIGH/MEDIUM/LOW + apply_low_confidence_penalty()
│   │   └── scrape_pipeline/
│   │       ├── __init__.py            [✅ Phase 1]
│   │       ├── linkedin_scraper.py    [✅ Phase 1] Playwright stub — structure done, impl TODO
│   │       ├── instagram_scraper.py   [✅ Phase 1] Playwright stub — structure done, impl TODO
│   │       └── signal_extractor.py    [✅ Phase 1] Bilingual EN+ID keyword sets; all signal types
│   │
│   ├── signal_delta/
│   │   ├── __init__.py                [✅ Phase 1]
│   │   ├── delta_scraper.py           [✅ Pre-Phase 6 fix] DeltaScraper class — LinkedIn/Instagram delta scrape
│   │   ├── delta_classifier.py        [✅ Pre-Phase 6 fix] DeltaClassifier class — keyword → DeltaSignalType
│   │   ├── observed_state_injector.py [✅ Pre-Phase 6 fix] ObservedStateInjector — RWI adjustment; NEVER writes genome
│   │   └── delta_pipeline.py          [✅ Pre-Phase 6 fix] FACADE — re-exports 3 classes + run_signal_delta_pipeline()
│   │
│   ├── session/
│   │   ├── __init__.py                [✅ Phase 1]
│   │   ├── session_models.py          [✅ Phase 1] SessionRecord, SessionEvent, ParalinguisticSnapshot
│   │   ├── session_init.py            [✅ Pre-Phase 6 fix] PsychFlagDisplay renamed (flag_type/message/recommendation); ConfidenceBadge.color (was color_hint); MEDIUM=yellow (was amber)
│   │   ├── session_runner.py          [✅ Phase 3] Zone 2 event loop — Stream A + Stream B + logger asyncio.gather
│   │   ├── session_logger.py          [✅ Phase 3] JSONL event log; 4 event types; async non-blocking writes
│   │   └── session_analyzer.py        [✅ Pre-Phase 6 fix] _enrich_candidate_for_mobile() added; to_dict() calls enrichment for mobile UI fields
│   │
│   ├── audio/
│   │   ├── __init__.py                [✅ Phase 3]
│   │   ├── audio_bridge.py            [✅ Phase 3] BLE receiver stub; AudioBridgeConfig; receive_bytes → AudioBuffer
│   │   ├── audio_buffer.py            [✅ Phase 3] 50ms chunks; asyncio.Queue; fans to Stream A + B
│   │   ├── transcription_engine.py    [✅ Phase 3] 30-chunk window; lazy Whisper load; stub mode
│   │   ├── audio_signal_processor.py  [✅ Phase 3] RMS/ZCR/spectral/pitch; librosa optional; numpy fallback
│   │   └── paralinguistic_extractor.py [✅ Phase 3] 90s baseline; 5 signals per PRD 3.1a; BASELINE_DURATION_S=90
│   │
│   ├── classifier/
│   │   ├── __init__.py                [✅ Phase 3]
│   │   ├── moment_classifier.py       [✅ Phase 3] Dispatcher; LOCAL_CONFIDENCE_THRESHOLD=0.45; ClassificationResult
│   │   ├── local_classifier.py        [✅ Phase 3] Bilingual EN+ID patterns; basa-basi suppression
│   │   ├── slm_classifier.py          [✅ Phase 3] SLM fallback; Indonesian B2B classification prompt
│   │   └── divergence_detector.py     [✅ Phase 3] 3 divergence checks; TENSION_HIGH=0.55; DivergenceAlert
│   │
│   ├── slm/
│   │   ├── __init__.py                [✅ Phase 3]
│   │   ├── slm_warmer.py              [✅ Phase 3] Pre-load + 250ms cold latency check; WarmUpResult
│   │   ├── slm_runner.py              [✅ Phase 3] asyncio.wait_for 350ms; "" on timeout; run_sync for executor
│   │   ├── slm_adapter.py             [✅ Phase 3] THE LIVE INTELLIGENCE LAYER; 3 concurrent adaptations; fallback
│   │   └── slm_config.py             [✅ Phase 3] SLMConfig Pydantic; model_exists property; from_zone2_config()
│   │
│   ├── rwi/
│   │   ├── __init__.py                [✅ Phase 1]
│   │   └── rwi_calculator.py         [✅ Phase 1] 4 components; delta signal adjustment; weighted formula
│   │
│   ├── bars/
│   │   ├── __init__.py                [✅ Phase 3]
│   │   └── bar_calculator.py         [✅ Phase 3] Moment delta tables; para modulation; genome modifiers; confidence scaling
│   │
│   ├── dialog/
│   │   ├── __init__.py                [✅ Phase 2]
│   │   ├── cache_builder.py           [✅ Phase 2] Zone 1 LLM call → validate → fill → probability adjust
│   │   ├── dialog_selector.py         [✅ Phase 3] Cache lookup; SLM adapt; hardcoded fallback; SelectionResult
│   │   └── probability_engine.py      [✅ Phase 2] Confidence compression + genome adjustments + RWI modifiers
│   │
│   ├── display/
│   │   ├── __init__.py                [✅ Phase 3]
│   │   ├── display_driver.py          [✅ Pre-Phase 6 fix] HUDPayload: added para + confidence_badge optional fields
│   │   ├── watch_driver.py            [✅ Phase 3] 3-word trigger extraction; auto-haptic on: type change/diverge/close>70
│   │   ├── phone_driver.py            [✅ Pre-Phase 6 fix] _build_hud_state() rewrite: rwi_live→object, confidence_badge, selection, para, divergence_alert top-level, elapsed_seconds
│   │   └── glasses_driver.py          [✅ Phase 3] STUB — all methods log and return; v2 placeholder
│   │
│   ├── practitioner/
│   │   ├── __init__.py                [✅ Phase 4]
│   │   ├── practitioner_profile.py    [✅ Phase 4] 10 params; EMA smoothing; strengths/development_areas
│   │   ├── practitioner_updater.py    [✅ Phase 4] Applies deltas; increments session_count; repo-optional
│   │   └── mirror_report.py           [✅ Phase 4] 4 observations; NEVER on live HUD (hardcoded); to_dict()
│   │
│   ├── psych_review/
│   │   ├── __init__.py                [✅ Phase 2]
│   │   ├── psych_review_agent.py      [✅ Phase 2] Orchestrates validity + ecological → PsychReviewReport
│   │   ├── validity_checker.py        [✅ Phase 2] Rule-based genome validity; 6 check types
│   │   └── ecological_validator.py    [✅ Phase 2] Indonesian B2B flags; 5 flag types (4 base + agreeableness conditional)
│   │
│   └── db/
│       ├── __init__.py                [✅ Phase 1]
│       ├── supabase_client.py         [✅ Phase 1] lru_cache singleton; raises if env vars missing
│       ├── genome_repo.py             [✅ Phase 1] CRUD + mutation log + last_scrape_timestamp; lazy client
│       └── session_repo.py            [✅ Pre-Phase 6 fix] Added get_session_by_prospect_id() for /session/start endpoint
│
├── mobile/
│   ├── package.json                   [✅ Phase 5] RN 0.73.4, ble-plx, watch-connectivity, zustand, react-navigation
│   ├── app.json                       [✅ Phase 5]
│   ├── index.js                       [✅ Phase 5]
│   ├── HANDOFF_phase5.md              [✅ Phase 5] Decisions, open issues, Phase 6 brief
│   │
│   └── src/
│       ├── App.tsx                    [✅ Phase 5] Root; mounts RootNavigator; dark StatusBar
│       ├── navigation/
│       │   └── RootNavigator.tsx      [✅ Phase 5] 4-screen stack; dark theme; landscape lock on LiveHUD
│       ├── screens/
│       │   ├── PreSessionScreen.tsx   [✅ Phase 5] Genome badge (Constraint #4); RWI; HIGH flag gate (Constraint #5); GO button
│       │   ├── LiveHUDScreen.tsx      [✅ Phase 5] 2-col landscape; Zustand only (no API calls); HUDWebSocketManager
│       │   ├── MutationReviewScreen.tsx [✅ Phase 5] Per-candidate confirm/dismiss; mutation gate enforced
│       │   └── MirrorReportScreen.tsx  [✅ Phase 5] 4 observations; NEVER live (Constraint #6); popToTop on Done
│       ├── components/
│       │   ├── HookCloseBar.tsx       [✅ Phase 5] hook/close bars; trend arrows; color tiers; compact prop
│       │   ├── DialogOptions.tsx      [✅ Phase 5] Sorted by probability; SLM-adapted badge; onSelect callback
│       │   ├── RWIIndicator.tsx       [✅ Phase 5] 4 window statuses; compact prop
│       │   ├── ConfidenceBadge.tsx    [✅ Phase 5] ALWAYS shown (Constraint #4); green/yellow/red; small/normal
│       │   ├── PsychWarningCard.tsx   [✅ Phase 5] HIGH must acknowledge (Constraint #5); MODERATE shown no gate
│       │   ├── MomentTypeLabel.tsx    [✅ Phase 5] 6 moment types; icons; confidence %
│       │   ├── HiddenSignalPanel.tsx  [✅ Pre-Phase 6 fix] Python field names: speech_rate_delta, volume_level, pause_duration, voice_tension_index, cadence_consistency_score
│       │   └── DivergenceAlert.tsx    [✅ Phase 5] verbal≠para alert; HIGH/MEDIUM severity; verbal_state vs para_state
│       ├── ble/
│       │   ├── BLEManager.ts          [✅ Phase 5] react-native-ble-plx; Plaud Note; MTU 512; dynamic require guard
│       │   └── AudioStreamer.ts        [✅ Phase 5] CHUNK_SIZE_BYTES=1600 (50ms); buffers; WS binary frame
│       ├── watch/
│       │   └── WatchBridge.ts         [✅ Phase 5] updateApplicationContext; sendMessage haptic; reachability sub
│       ├── services/
│       │   ├── SessionService.ts      [✅ Phase 5] Zone 1/3 HTTP; AbortController timeout; 8 methods
│       │   └── HUDStateManager.ts     [✅ Phase 5] Zustand store; HUDWebSocketManager; reconnect ×5
│       └── types/
│           └── index.ts               [✅ Pre-Phase 6 fix] BarState hook_score/close_score; ParalinguisticSignals Python field names; all other types verified correct
│
└── tests/
    ├── unit/
    │   ├── test_genome_resolver.py    [✅ Phase 1] 18 tests
    │   ├── test_rwi_calculator.py     [✅ Phase 1] 15 tests (incl. mutation gate)
    │   ├── test_moment_classifier.py  [✅ Phase 3] 15 tests: LocalClassifier(8) + MomentClassifier(7)
    │   ├── test_bar_calculator.py     [✅ Phase 3] 12 tests: initial state, deltas, clamp, trends, para, genome
    │   ├── test_dialog_selector.py    [✅ Phase 3] 10 tests: cache lookup, fallback, SLM adapt, error handling
    │   └── test_probability_engine.py [✅ Phase 2 — in test_zone1_pipeline.py]
    ├── integration/
    │   ├── test_zone1_pipeline.py     [✅ Phase 2] 27 tests: PsychReview(9) + ProbEngine(5) + CacheBuilder(5) + SessionInit(8)
    │   ├── test_zone2_loop.py         [✅ Phase 6] 21 tests: Init(3)+StreamA(5)+StreamB(4)+Divergence(3)+Logger(3)+Lifecycle(3)
    │   └── test_zone3_pipeline.py     [✅ Phase 4] 25 tests: SessionAnalyzer(8)+Profile(7)+Updater(5)+Mirror(5)
    └── latency/
        └── test_zone2_latency.py      [✅ Phase 6] 11 tests: SLMFallback(3)+Component(4)+FullPipeline(4); p95<400ms PASSING
```

---

## MODULE DEPENDENCY MAP

```
genome_resolver       depends on: supabase_client, genome_builder, confidence_scorer, scrape_pipeline
rwi_calculator        depends on: genome (data only)
psych_review_agent    depends on: genome (data only), validity_checker, ecological_validator
                      [LLM overlay handled by harness_runner separately]
cache_builder         depends on: genome (data), rwi_calculator (data), llm_client, probability_engine
session_init          depends on: genome_resolver (data), rwi_calculator (data), psych_review_agent, cache_builder
session_runner        depends on: audio_bridge, moment_classifier, bar_calculator, dialog_selector, display_driver, session_logger
audio_buffer          depends on: nothing
audio_bridge          depends on: audio_buffer
transcription_engine  depends on: audio_buffer (Stream A)
audio_signal_processor depends on: audio_buffer (Stream B)
paralinguistic_extractor depends on: audio_signal_processor
moment_classifier     depends on: local_classifier, slm_classifier (fallback), observed_state
divergence_detector   depends on: observed_state (verbal + paralinguistic fields)
slm_runner            depends on: slm_config
slm_warmer            depends on: slm_runner, slm_config
slm_adapter           depends on: slm_runner, cache (data), observed_state (data)
dialog_selector       depends on: cache (file), slm_adapter, probability_engine
bar_calculator        depends on: genome (data), observed_state (data)
display_driver        depends on: watch_driver | phone_driver | glasses_driver
session_analyzer      depends on: session_logger (data), llm_client, genome (data)
practitioner_updater  depends on: session_analyzer output, practitioner_profile
mirror_report         depends on: practitioner_profile (accumulated)
```

---

## HANDOFF LOG

| Date | Phase | Status | Notes |
|------|-------|--------|-------|
| April 2026 | Seed v1.1 | ✅ Complete | PRD, CLAUDE.md, skills, FILE_TREE created |
| April 2026 | Phase 1: Foundation | ✅ Complete | 33/33 tests. DB lazy client fix applied. |
| April 2026 | Phase 2: Zone 1 Pipeline | ✅ Complete | 60/60 tests. See HANDOFF_phase2.md. |
| April 2026 | Phase 3: Zone 2 Engine | ✅ Complete | 97/97 tests. See HANDOFF_phase3.md. |
| April 2026 | Phase 4: Zone 3 Pipeline | ✅ Complete | 122/122 tests. See HANDOFF_phase4.md. |
| April 2026 | Phase 5: Mobile App | ✅ Complete | All RN files written. No TS test runner run (TypeScript files). See mobile/HANDOFF_phase5.md. |
| April 2026 | Pre-Phase 6 Fixes | ✅ Complete | 14-bug adversarial fix pass. See pantheonv2-guide-implementation/PRETEST_HANDOFF.md. All Groups A–G applied. |
| April 2026 | Phase 6: Tests | ✅ Complete | 154/154 tests passing. Zone 2 p95 <400ms CONFIRMED. 2 bugs fixed in session_runner.py (detect/process_chunk). See mobile/HANDOFF_phase6.md. |

---

*End of FILE_TREE.md*
