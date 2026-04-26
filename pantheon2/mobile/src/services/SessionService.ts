/**
 * SessionService.ts — Backend API client for Pantheon 2.0 mobile app.
 *
 * Handles all HTTP communication with the FastAPI backend.
 * Zone 2 is local-only (no API calls during live session) — all calls
 * in this service are Zone 1 (pre-session setup) or Zone 3 (post-session).
 *
 * Base URL is read from environment or defaults to localhost for dev.
 */

import type {
  PreSessionPayload,
  MutationReviewPayload,
  MirrorReportPayload,
} from '../types';

// ------------------------------------------------------------------ //
// Config                                                               //
// ------------------------------------------------------------------ //

const BASE_URL: string =
  (typeof process !== 'undefined' && process.env?.PANTHEON_API_URL) ||
  'http://localhost:8000';

const DEFAULT_TIMEOUT_MS = 10_000;

// ------------------------------------------------------------------ //
// Helpers                                                              //
// ------------------------------------------------------------------ //

async function apiGet<T>(path: string): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT_MS);

  try {
    const response = await fetch(`${BASE_URL}${path}`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
      signal: controller.signal,
    });
    if (!response.ok) {
      throw new Error(`API GET ${path} failed: ${response.status}`);
    }
    return response.json() as Promise<T>;
  } finally {
    clearTimeout(timer);
  }
}

async function apiPost<T>(path: string, body: object): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT_MS);

  try {
    const response = await fetch(`${BASE_URL}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal: controller.signal,
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      throw new Error(`API POST ${path} failed: ${response.status}`);
    }
    return response.json() as Promise<T>;
  } finally {
    clearTimeout(timer);
  }
}

// ================================================================== //
//  SESSION SERVICE                                                     //
// ================================================================== //

export const SessionService = {
  /**
   * Zone 1: Prepare a session (genome load, RWI, cache build, psych review).
   * Called when practitioner starts the pre-session flow.
   * Response: PreSessionPayload — includes session_id for subsequent calls.
   */
  prepareSession: async (
    prospectId: string,
    practitionerId: string = 'practitioner_001',  // TODO: replace with auth-provided ID
  ): Promise<PreSessionPayload> => {
    return apiPost('/session/prepare', {
      prospect_id: prospectId,
      practitioner_id: practitionerId,
    });
  },

  /**
   * Zone 1: Acknowledge a HIGH severity psych flag.
   * Practitioner must acknowledge all HIGH flags before GO is unlocked.
   * session_id comes from PreSessionPayload.session_id.
   */
  acknowledgeFlag: async (flagId: string): Promise<void> => {
    await apiPost('/session/acknowledge_flag', { flag_id: flagId });
  },

  /**
   * Zone 1 → Zone 2 transition: Signal practitioner GO.
   * Backend starts session_runner. Returns confirmed session_id.
   */
  startSession: async (prospectId: string): Promise<{ session_id: string }> => {
    return apiPost('/session/start', { prospect_id: prospectId });
  },

  /**
   * Zone 2 → Zone 3 transition: End session.
   * Backend stops session_runner and triggers Zone 3 analysis.
   */
  endSession: async (sessionId: string): Promise<{ ended: boolean }> => {
    return apiPost(`/session/${sessionId}/end`, {});
  },

  /**
   * Zone 2: Record practitioner option choice (tap on a dialog option).
   * Logged by session_logger for Zone 3 analysis.
   */
  recordOptionChoice: async (
    sessionId: string,
    optionKey: 'option_a' | 'option_b' | 'option_c',
  ): Promise<void> => {
    await apiPost(`/session/${sessionId}/option_choice`, { option_key: optionKey });
  },

  /**
   * Zone 3: Poll for session analysis result.
   * Called after session ends while Zone 3 LLM runs.
   * Returns null if not ready yet.
   */
  getAnalysis: async (sessionId: string): Promise<MutationReviewPayload | null> => {
    try {
      return await apiGet<MutationReviewPayload>(`/session/${sessionId}/analysis`);
    } catch {
      return null;
    }
  },

  /**
   * Zone 3: Confirm or dismiss a mutation candidate.
   * Confirmed mutations are passed to genome_writer.py for gate validation.
   */
  respondToMutation: async (
    sessionId: string,
    candidateId: string,
    decision: 'confirm' | 'dismiss',
  ): Promise<void> => {
    await apiPost(`/session/${sessionId}/mutation/respond`, {
      candidate_id: candidateId,
      decision,
    });
  },

  /**
   * Zone 3: Fetch Mirror Report after analysis completes.
   * Only called from MirrorReportScreen — never during live session.
   */
  getMirrorReport: async (sessionId: string): Promise<MirrorReportPayload | null> => {
    try {
      return await apiGet<MirrorReportPayload>(`/session/${sessionId}/mirror_report`);
    } catch {
      return null;
    }
  },

  /**
   * Health check — used by PreSessionScreen to verify backend is reachable.
   */
  healthCheck: async (): Promise<boolean> => {
    try {
      await apiGet('/health');
      return true;
    } catch {
      return false;
    }
  },
};
