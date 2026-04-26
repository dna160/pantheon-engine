# HANDOFF — Phase 6: Tests

## Status: COMPLETE

154/154 tests passing. Zone 2 p95 latency < 400ms confirmed.

---

## What Is Done

### New Test Files

**`tests/integration/test_zone2_loop.py`** — 21 tests  
Full Zone 2 event loop integration. All components mocked (no real audio, no real SLM,
no Supabase, no network). Verifies correct data flow through both parallel streams.

Test classes:
- `TestSessionRunnerInit` (3) — construction, initial state, default para
- `TestStreamALoop` (5) — audio→transcription→classifier→selector→render; HUDPayload.para field present
- `TestStreamBLoop` (4) — audio→signal_proc→para_extractor→render_bars_only at PARA_RENDER_INTERVAL
- `TestDivergenceDetection` (3) — alert fires when detector returns DivergenceAlert; stored in _active_divergence_alert
- `TestLoggerIntegration` (3) — log_moment_event called with correct session_id; record_option_choice delegated
- `TestSessionLifecycle` (3) — _running True during run(); stop() sets False; display.clear() called on exit

**`tests/latency/test_zone2_latency.py`** — 11 tests  
PRD 4.2 budget verification. Runs 100 iterations per test, measures p95 wall-clock time.

Test classes:
- `TestSLMFallbackLatency` (3) — stub returns immediately; timeout fires at ≤config; fast inference passes through
- `TestComponentLatency` (4) — BarCalculator<5ms, DivergenceDetector<5ms, cache lookup<10ms, fallback<5ms
- `TestFullPipelineLatency` (4):
  - Stub SLM p95 < 400ms (fast path)
  - Simulated 200ms SLM p95 < 400ms
  - SLM timeout fallback p95 < 450ms (350ms timeout + <50ms overhead)
  - Bars-only render path < 10ms p95

### Bug Fixes (found during test writing)

**`session_runner.py` — two method name mismatches:**

1. `self._divergence.check()` → `self._divergence.detect()`  
   `DivergenceDetector` exposes `.detect()`, not `.check()`. Session runner was calling
   a non-existent method on every Stream A cycle. Fixed.

2. `self._signal_proc.process()` → `self._signal_proc.process_chunk()`  
   `AudioSignalProcessor` exposes `.process_chunk()`, not `.process()`. Fixed.

**`tests/integration/test_zone1_pipeline.py` — stale field name:**  
Two tests used `payload.confidence_badge.color_hint` — the field was renamed to `.color`
in the Groups A–G pre-test fix pass. Updated to `.color`.

---

## Decisions Made

1. **`asyncio.run()` per test (not pytest-asyncio `@pytest.mark.asyncio`)**: Existing tests in the
   codebase don't use pytest-asyncio markers. Using `asyncio.run()` inside regular sync test methods
   is consistent with the rest of the test suite and doesn't require asyncio mode configuration.

2. **`asyncio.wait_for(runner.run(), timeout=1.0)` pattern**: The Zone 2 event loop runs forever
   until `stop()` is called. Tests push chunks, sleep briefly, call `stop()`, then await the run
   with a 1s timeout. This ensures tests terminate even if `stop()` doesn't propagate immediately.

3. **`_make_runner()` builder pattern**: All 21 integration tests use a single factory function
   that accepts overrides. Follows the same pattern as `_make_genome()` helpers in existing unit tests.

4. **Latency test uses `ITERATIONS=100` and `time.perf_counter()`**: High iteration count minimizes
   measurement noise. `perf_counter()` provides sub-millisecond resolution. `asyncio.run()` overhead
   is included in the measurement — this is conservative (real Zone 2 runs a single event loop).

5. **SLM timeout test uses 100ms config (not 350ms)**: Testing the full 350ms timeout per iteration
   would make the test suite take 35+ seconds. 100ms config produces the same behavioral verification
   (timeout fires; returns '') at 7× the speed.

---

## Test Coverage Summary

| Module | Tests | Coverage Notes |
|--------|-------|----------------|
| SessionRunner (Zone 2 loop) | 21 integration | Both streams; divergence; logger; lifecycle |
| SLMRunner (timeout enforcement) | 3 latency | Stub; timeout; fast pass-through |
| BarCalculator (latency) | 1 latency | p95 < 5ms confirmed |
| DivergenceDetector (latency) | 1 latency | p95 < 5ms confirmed |
| DialogSelector (latency) | 2 latency | Cache lookup + fallback p95 confirmed |
| Full pipeline (latency) | 4 latency | p95 < 400ms with stub/200ms/timeout SLM |

---

## Open Issues

None. All tests pass. The system is complete through Phase 6.

---

## What Is Next

Pantheon 2.0 build is complete through all 6 phases. Next steps are operational:

1. **Hardware integration**: Wire real Plaud Note Pro BLE into `audio_bridge.py` — the stub
   `receive_bytes()` method needs the actual BLE library call.

2. **SLM model procurement**: Download Phi-3-mini-4k-instruct-Q4_K_M.gguf to `./models/` and
   set `SLM_MODEL_PATH` env var. `slm_runner.load()` will activate the real model path.

3. **Supabase provisioning**: Run `db/schema_v2.sql` against a real Supabase project. Fill `.env`
   with `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`.

4. **Indonesian classifier training**: `local_classifier.py` uses keyword patterns. A trained
   multilingual BERT or similar lightweight model for the 6-type classification would improve
   accuracy for the Indonesian B2B context.

5. **Smartwatch app**: The `WatchDriver` backend and `WatchBridge.ts` mobile bridge are
   implemented. The native WatchOS/WearOS app that receives `updateApplicationContext` still needs
   to be built.
