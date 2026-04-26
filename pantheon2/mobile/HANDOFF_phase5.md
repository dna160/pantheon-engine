# HANDOFF — Phase 5: React Native Mobile App

## Status: COMPLETE

All Phase 5 files written and internally consistent.

---

## What Is Done

### BLE / Audio
- `mobile/src/ble/BLEManager.ts` — react-native-ble-plx wrapper; Plaud Note Pro scan/connect/stream/disconnect; MTU 512; dynamic require guard for test environments
- `mobile/src/ble/AudioStreamer.ts` — CHUNK_SIZE_BYTES=1600 (50ms@16kHz PCM16); buffers BLE bytes; flushes complete chunks via WebSocket binary frame to ws://localhost:8000/ws/audio/{sessionId}

### Watch Bridge
- `mobile/src/watch/WatchBridge.ts` — react-native-watch-connectivity wrapper; updateApplicationContext for state push; sendMessage for haptic patterns; reachability subscription with auto-resend; dynamic require guard

### Services
- `mobile/src/services/SessionService.ts` — Zone 1/3 HTTP client; AbortController timeout; methods: prepareSession, acknowledgeFlag, startSession, endSession, recordOptionChoice, getAnalysis, respondToMutation, getMirrorReport, healthCheck
- `mobile/src/services/HUDStateManager.ts` — Zustand store (useHUDStore); HUDWebSocketManager class (connect/disconnect/reconnect up to 5x); handles full and bars-only WS messages

### Components (8 total)
- `mobile/src/components/HookCloseBar.tsx` — hook/close bars with trend arrows and color tiers
- `mobile/src/components/DialogOptions.tsx` — 3 options sorted by probability descending; SLM-adapted badge; fallback badge; onSelect callback
- `mobile/src/components/ConfidenceBadge.tsx` — always shown (Constraint #4); green/yellow/red; small/normal size
- `mobile/src/components/RWIIndicator.tsx` — 4 window statuses; compact prop
- `mobile/src/components/MomentTypeLabel.tsx` — 6 moment types with icons and confidence %
- `mobile/src/components/PsychWarningCard.tsx` — HIGH/MODERATE/LOW; acknowledge button for HIGH (Constraint #5)
- `mobile/src/components/HiddenSignalPanel.tsx` — Stream B paralinguistics: speech_rate_wpm, volume_trend, pause_frequency, tension_score, pitch_variance, vocal_fry_detected; phone-only
- `mobile/src/components/DivergenceAlert.tsx` — verbal ≠ para mismatch; HIGH/MEDIUM severity; active flag; verbal_state vs para_state display

### Navigation & Root
- `mobile/src/navigation/RootNavigator.tsx` — @react-navigation/native-stack; 4 screens; dark theme; landscape lock on LiveHUD
- `mobile/src/App.tsx` — root; StatusBar dark; mounts RootNavigator

### Screens (4 total)
- `mobile/src/screens/PreSessionScreen.tsx` — genome confidence badge (always), RWI, HIGH psych flag acknowledgment gate, GO button; calls prepareSession on mount
- `mobile/src/screens/LiveHUDScreen.tsx` — landscape; 2-col layout; reads Zustand only (no API calls during Zone 2); HUDWebSocketManager; END button with confirmation
- `mobile/src/screens/MutationReviewScreen.tsx` — post-session; per-candidate confirm/dismiss; mutation gate enforced; navigates to MirrorReport when all resolved
- `mobile/src/screens/MirrorReportScreen.tsx` — post-session ONLY (Constraint #6); 4 observation cards; session stats; strengths/development pills; popToTop on Done

### Types
- `mobile/src/types/index.ts` — complete TypeScript types mirroring Python models; BarState uses `hook`/`close` (not `hook_score`/`close_score`); ParalinguisticSignals has Stream B fields; DivergenceAlert has `active`, `severity`, `verbal_state`, `para_state`; HUDState has `selection`, `para`, `divergence_alert`, `elapsed_seconds`, `confidence_badge`, `classification_confidence`; full MirrorReportPayload with flat observation fields; MutationCandidate with `candidate_id`, `direction`, `rationale`

---

## Decisions Made

1. **BarState field names**: Used `hook` and `close` (not `hook_score`/`close_score`) — cleaner and consistent with bar_calculator.py naming intent. Backend responses that use the longer names are handled at the service layer.

2. **HUDWebSocketManager constructor**: Takes only `(sessionId, baseUrl?)` — all state updates go through `useHUDStore.getState()` internally. No callbacks in constructor.

3. **prepareSession signature**: Returns `PreSessionPayload` directly (session_id is inside payload). Avoids nested `{ session_id, payload }` pattern.

4. **acknowledgeFlag signature**: Takes only `flagId` — endpoint is `/session/acknowledge_flag` (not session-namespaced) because at pre-session the session_id lives in the payload already.

5. **respondToMutation**: Uses `candidateId: string` not `candidateIndex: number` — more robust, matches how backend will identify candidates.

6. **MirrorReportPayload**: Flat `what_worked`, `what_didnt`, `pattern_detected`, `next_session_focus` fields plus session stats. Keeps legacy `observations` and `profile_context` nested fields as optional for backend compatibility.

7. **DivergenceAlert type**: Added `active: boolean` as primary gate. Severity is `'HIGH' | 'MEDIUM' | 'LOW'` (uppercase string union, not `AlertSeverity` type alias — consistency with other severity types in the file).

8. **PreSession navigation param**: `{ prospectId?: string } | undefined` — optional so screen can show with a default 'demo' prospect when launched directly.

---

## Open Issues

- `@react-navigation/native-stack` must be installed alongside `@react-navigation/native` — add to package.json if not present
- `orientation: 'landscape'` in RootNavigator requires `react-native-screens` and iOS Info.plist `UISupportedInterfaceOrientations` config
- `HUDWebSocketManager` uses `useHUDStore.getState()` (static Zustand access) — works in RN but requires Zustand ≥4.x
- Backend `/session/prepare` endpoint must return `PreSessionPayload` shape including `prospect_name`, `role`, `company` — verify session_init.py response serialization matches

---

## What Is Next

**Phase 6: Tests**
- `tests/integration/test_zone2_loop.py` — full Zone 2 loop integration (mock BLE + mock SLM + verify latency)
- `tests/latency/test_zone2_latency.py` — must pass <400ms p95 for classify → adapt → render pipeline

Build order for Phase 6:
1. Read `backend/session/session_runner.py` — understand the asyncio.gather loop
2. Read `backend/slm/slm_runner.py` — understand the 350ms timeout + fallback
3. Write `test_zone2_loop.py` with mock audio streams
4. Write `test_zone2_latency.py` with percentile assertions
