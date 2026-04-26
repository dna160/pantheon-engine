/**
 * HUDStateManager.ts — Zone 2 local HUD state store (Zustand).
 *
 * CRITICAL: No API calls during Zone 2. All state updates come from the
 * WebSocket connection to the backend phone_driver emitter.
 *
 * This store is the single source of truth for the live HUD.
 * All Zone 2 screens read from this store — never from the API.
 *
 * State updates are pushed by the backend PhoneDriver → WebSocket → here.
 * The store is reset when the session ends.
 */

import { create } from 'zustand';
import type { HUDState, BarState, MomentType } from '../types';

// ------------------------------------------------------------------ //
// Default / initial state                                              //
// ------------------------------------------------------------------ //

const DEFAULT_BARS: BarState = {
  hook_score: 50,     // matches Python BarState.hook_score
  close_score: 30,    // matches Python BarState.close_score
  hook_trend: 'stable',
  close_trend: 'stable',
};

const DEFAULT_HUD_STATE: HUDState = {
  bars: DEFAULT_BARS,
  moment_type: 'neutral_exploratory',
  classification_confidence: 0.5,
  confidence_badge: { level: 'MEDIUM', label: 'Medium Confidence', color: 'yellow' },
  rwi_live: { score: 50, window_status: 'open' },
  selection: null,
  para: null,
  divergence_alert: null,
  elapsed_seconds: 0,
  selected_key: null,
  timestamp: null,
};

// ------------------------------------------------------------------ //
// Store interface                                                       //
// ------------------------------------------------------------------ //

interface HUDStoreState {
  // Current HUD state
  hud: HUDState;
  isSessionActive: boolean;
  sessionId: string | null;
  wsConnected: boolean;

  // Actions
  updateHUD: (update: Partial<HUDState> | HUDState) => void;
  updateBarsOnly: (bars: BarState) => void;
  setSessionActive: (active: boolean, sessionId?: string) => void;
  setWSConnected: (connected: boolean) => void;
  resetSession: () => void;
}

// ================================================================== //
//  ZUSTAND STORE                                                       //
// ================================================================== //

export const useHUDStore = create<HUDStoreState>((set) => ({
  hud: DEFAULT_HUD_STATE,
  isSessionActive: false,
  sessionId: null,
  wsConnected: false,

  updateHUD: (update) =>
    set((state) => ({
      hud: { ...state.hud, ...update },
    })),

  updateBarsOnly: (bars) =>
    set((state) => ({
      hud: { ...state.hud, bars },
    })),

  setSessionActive: (active, sessionId) =>
    set({ isSessionActive: active, sessionId: sessionId ?? null }),

  setWSConnected: (connected) =>
    set({ wsConnected: connected }),

  resetSession: () =>
    set({
      hud: DEFAULT_HUD_STATE,
      isSessionActive: false,
      sessionId: null,
      wsConnected: false,
    }),
}));

// ================================================================== //
//  WEBSOCKET MANAGER                                                   //
// ================================================================== //

/**
 * Manages the WebSocket connection to the backend PhoneDriver emitter.
 * Opens during Zone 2 (after GO signal). Closes when session ends.
 *
 * Zone 2 constraint: this receives data from backend — it never calls
 * any external API. The WS connection is to our own backend only.
 */
export class HUDWebSocketManager {
  private ws: WebSocket | null = null;
  private sessionId: string;
  private baseUrl: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelayMs = 1000;

  constructor(sessionId: string, baseUrl: string = 'ws://localhost:8000') {
    this.sessionId = sessionId;
    this.baseUrl = baseUrl;
  }

  connect(): void {
    const url = `${this.baseUrl}/ws/hud/${this.sessionId}`;

    try {
      this.ws = new WebSocket(url);

      this.ws.onopen = () => {
        useHUDStore.getState().setWSConnected(true);
        this.reconnectAttempts = 0;
      };

      this.ws.onmessage = (event) => {
        this._handleMessage(event.data);
      };

      this.ws.onclose = () => {
        useHUDStore.getState().setWSConnected(false);
        this._maybeReconnect();
      };

      this.ws.onerror = () => {
        useHUDStore.getState().setWSConnected(false);
      };
    } catch {
      // WebSocket not available (test environment)
    }
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    useHUDStore.getState().setWSConnected(false);
  }

  private _handleMessage(data: string): void {
    try {
      const payload = JSON.parse(data) as Partial<HUDState> & { _session_ended?: boolean };

      if (payload._session_ended) {
        useHUDStore.getState().setSessionActive(false);
        return;
      }

      // Bars-only update (lightweight)
      if (payload.bars && Object.keys(payload).length === 1) {
        useHUDStore.getState().updateBarsOnly(payload.bars);
        return;
      }

      // Full HUD update
      useHUDStore.getState().updateHUD(payload);
    } catch {
      // Malformed message — ignore
    }
  }

  private _maybeReconnect(): void {
    if (!useHUDStore.getState().isSessionActive) return;
    if (this.reconnectAttempts >= this.maxReconnectAttempts) return;

    this.reconnectAttempts += 1;
    setTimeout(() => this.connect(), this.reconnectDelayMs * this.reconnectAttempts);
  }
}
