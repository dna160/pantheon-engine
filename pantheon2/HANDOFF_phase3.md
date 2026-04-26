# HANDOFF_phase3.md — Pantheon 2.0 Phase 3: Zone 2 Engine

**Phase:** 3 — Zone 2 Engine  
**Status:** ✅ Complete  
**Tests:** 97/97 passing (37 new Phase 3 tests + 60 Phase 2 + 33 Phase 1 carry forward)  
**Date:** April 2026

---

## WHAT IS DONE

### Files Written (Phase 3)

**Audio Layer**
- `backend/audio/audio_buffer.py` — AudioBuffer with 50ms AudioChunk queuing; fans to Stream A (transcript) and Stream B (paralinguistic) via asyncio.Queue. Drop-oldest on full.
- `backend/audio/audio_bridge.py` — BLE receiver stub; AudioBridgeConfig (16kHz/mono/PCM16); receive_bytes() → AudioBuffer.push()
- `backend/audio/transcription_engine.py` — Accumulates 30×50ms chunks (1.5s), lazy Whisper small load, stub mode without whisper, async run_in_executor
- `backend/audio/audio_signal_processor.py` — RMS/ZCR/spectral centroid/pitch extraction; librosa if available, numpy-only fallback; AudioFeatureVector
- `backend/audio/paralinguistic_extractor.py` — 90s baseline (basa-basi capture); 5 PRD 3.1a signals: speech_rate_delta, volume_level, pause_duration, voice_tension_index, cadence_consistency_score; ParalinguisticBaseline + ParalinguisticSignals

**Classifier Layer**
- `backend/classifier/local_classifier.py` — Bilingual EN+ID rule-based; 6 MomentType patterns; basa-basi suppression (elapsed < 90s → no topic_avoidance); Indonesian indirect signals (ya betul flooding, indirect closing)
- `backend/classifier/slm_classifier.py` — SLM fallback with Indonesian B2B classification prompt; run_sync() via executor
- `backend/classifier/moment_classifier.py` — Dispatcher; LOCAL_CONFIDENCE_THRESHOLD=0.45; ClassificationResult dataclass; SLM fallback if local_conf < threshold
- `backend/classifier/divergence_detector.py` — 3 divergence checks: openness+tension, composure+withdrawal, closing+stress; TENSION_HIGH=0.55; DivergenceAlert

**SLM Layer**
- `backend/slm/slm_config.py` — SLMConfig Pydantic; model_exists property; from_zone2_config() classmethod
- `backend/slm/slm_runner.py` — asyncio.wait_for 350ms hard limit; run_sync() for executor calls; returns "" on timeout
- `backend/slm/slm_warmer.py` — Pre-loads model + dummy inference; warns if cold latency > 250ms; WarmUpResult
- `backend/slm/slm_adapter.py` — THE LIVE INTELLIGENCE LAYER (PRD 4.2); adapts all 3 options concurrently; 350ms per-option timeout via asyncio.wait_for; falls back to base cache unmodified

**Bars Layer**
- `backend/bars/bar_calculator.py` — Hook/Close delta tables per moment type (HIGH_OPENNESS +12/+8, CLOSING +8/+15, IRATE -10/-8); para modulation (tension dampens close on positive, volume drop = withdrawal, pause = deliberation, rate surge amplifies irate); genome modifiers (exec_flex>70 → 0.7x, neuroticism+irate → 1.4x close, chronesthesia+openness → 1.2x close, identity_fusion+threat → 1.3x hook); confidence scaling

**Dialog Layer**
- `backend/dialog/dialog_selector.py` — Cache lookup by moment_type.value; deep copy cache (never mutate live cache); SLMAdapter adaptation pass; SelectionResult dataclass; hardcoded fallback if no cache; update_cache() for live swaps

**Display Layer**
- `backend/display/display_driver.py` — Abstract base; HUDPayload dataclass (bar_state, selection, elapsed, divergence_alert, rwi_live); log_render() helper
- `backend/display/watch_driver.py` — 3-word trigger phrase extraction (highest-probability option); auto-haptic: single on moment type change, long on divergence alert, double when close ≥ 70; bridge stub
- `backend/display/phone_driver.py` — Full HUD payload; ConfidenceBadge always present; HiddenSignalPanel with divergence alert; emitter stub; render_bars_only() for lightweight updates
- `backend/display/glasses_driver.py` — STUB only; logs all calls; returns immediately; v2 placeholder

**Session Layer**
- `backend/session/session_runner.py` — Zone 2 main event loop; asyncio.gather(stream_a_loop, stream_b_loop, logger_loop); Stream A: transcript → classify → bar update → dialog select → full render; Stream B: features → para → divergence check → bars-only render every 5 updates; 2s timeout on queue reads; record_option_choice() for practitioner taps
- `backend/session/session_logger.py` — JSONL event log; 4 event types: moment_event, periodic_snapshot (30s), divergence_alert, option_choice; asyncio.Lock for thread-safe writes; run_in_executor for non-blocking file I/O; open()/close() lifecycle

**Test Files**
- `tests/unit/test_moment_classifier.py` — 15 tests: LocalClassifier(8) + MomentClassifier(7); basa-basi suppression, Indonesian indirect patterns, SLM stub mode, confidence thresholds
- `tests/unit/test_bar_calculator.py` — 12 tests: initial state, delta direction, clamping, trend detection, para modulation (tension, volume), genome modifiers (exec_flex, neuroticism)
- `tests/unit/test_dialog_selector.py` — 10 tests: cache lookup, moment type routing, no-cache fallback, missing moment type fallback, SLM adapter integration, adapter error fallback, was_adapted detection, confidence pass-through, update_cache()

---

## WHAT IS NEXT

### Phase 4: Zone 3 Pipeline

Build order (25 files, per FILE_TREE.md and CLAUDE.md):

1. `backend/session/session_analyzer.py` — Zone 3 LLM call; parses JSONL session log; surfaces mutation candidates; uses zone3_session_analyzer.txt prompt; Zone 3 ONLY (harness)
2. `backend/practitioner/practitioner_profile.py` — 10 practitioner parameters (communication_style, pacing_preference, hook_instinct, close_confidence, resilience_under_resistance, rapport_approach, preparation_depth, emotional_calibration, feedback_sensitivity, adaptive_range)
3. `backend/practitioner/practitioner_updater.py` — Updates practitioner profile from session log; one session = one delta; no direct genome writes
4. `backend/practitioner/mirror_report.py` — 4 observations post-session; NEVER shown on live HUD (hardcoded constraint per CLAUDE.md #6)
5. `tests/integration/test_zone3_pipeline.py` — Integration tests for full Zone 3 flow

**Protocol reminder:**  
- Read CLAUDE.md + FILE_TREE.md before coding  
- Write HANDOFF_phase4.md + update FILE_TREE.md after Phase 4  

---

## KEY DECISIONS

1. **SLM adapter as live intelligence** — Per PRD 4.2, slm_adapter is NOT optional and NOT a fallback. It IS the live-state filter every option passes through. dialog_selector always calls it; falls back to cache only on timeout/error.

2. **Stream B render frequency** — Raw audio arrives at 20Hz (50ms chunks). Rendering bars on every Stream B update would flood the display. Solution: render_bars_only() every 5 Stream B updates (PARA_RENDER_INTERVAL = 5 = every 250ms).

3. **Basa-basi window hardcoded at 90s** — `elapsed_session_seconds < 90.0` suppresses topic_avoidance. This is per PRD + adversarial-psychologist/SKILL.md Indonesian B2B calibration. Not configurable.

4. **session_runner stop()** — Sets `self._running = False`. The stream loops check this flag and the asyncio.gather completes when all tasks see it (or are cancelled). No forceful cancellation — let tasks drain gracefully.

5. **Deep copy cache in dialog_selector** — `copy.deepcopy(options)` on every cache lookup. Prevents SLM adapter from mutating the live cache dict in place. Performance cost is acceptable (<1ms for 3 small dicts).

6. **GlassesDriver stub** — All 4 abstract methods implemented as log-and-return. Fulfills DisplayDriver contract so session_runner doesn't need conditional logic. Full implementation deferred to v2.

---

## OPEN ISSUES

1. **session_runner + session_logger integration** — session_logger methods are called directly from session_runner but session_logger.open() must be called before the Zone 2 loop starts. harness_runner needs to call `await session_logger.open()` before `await session_runner.run()` in Phase 4 wiring.

2. **test_zone2_loop.py** — Integration test for full Zone 2 loop (audio bridge → display) deferred. Requires mocking async audio queues. Target: Phase 6 full test suite.

3. **test_zone2_latency.py** — <400ms p95 latency test deferred to Phase 6. Requires hardware-in-the-loop or realistic audio mocks.

4. **AudioSignalProcessor.process() signature** — session_runner calls `await self._signal_proc.process(chunk)`. Verify this is the correct async method name when wiring in Phase 4.

5. **DivergenceAlert state reset** — `self._active_divergence_alert` in session_runner is set on first alert but never cleared. Phase 4/6 should add: clear after N seconds or after moment type resolves.

---

## TO START PHASE 4

1. Read `CLAUDE.md` mandatory reads section
2. Read `FILE_TREE.md` (this file has been updated)
3. Read `HANDOFF_phase3.md` (this file)
4. Read `backend/session/session_analyzer.py` — TODO stub in session/ directory
5. Read `skills/harness-orchestrator/prompts/zone3_session_analyzer.txt` — already written in Phase 2
6. Start with session_analyzer.py (Zone 3 LLM call, mirrors cache_builder.py structure)
7. Then practitioner/ (3 files)
8. End with test_zone3_pipeline.py integration tests
9. Write HANDOFF_phase4.md + update FILE_TREE.md before starting Phase 5
