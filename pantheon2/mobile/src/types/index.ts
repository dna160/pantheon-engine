/**
 * types/index.ts — Shared TypeScript types for Pantheon 2.0 mobile app.
 * Mirrors backend Python dataclasses/Pydantic models exactly.
 * Single source of truth for all cross-component data shapes.
 */

// ================================================================== //
//  GENOME & CONFIDENCE                                                 //
// ================================================================== //

export type ConfidenceLevel = 'HIGH' | 'MEDIUM' | 'LOW';

export type MomentType =
  | 'neutral_exploratory'
  | 'irate_resistant'
  | 'topic_avoidance'
  | 'identity_threat'
  | 'high_openness'
  | 'closing_signal';

export type MutationStrength = 'WEAK' | 'MODERATE' | 'STRONG';

// ================================================================== //
//  RWI (RECEPTIVITY WINDOW INDEX)                                      //
// ================================================================== //

export type RWIWindowStatus = 'closed' | 'narrowing' | 'open' | 'peak';

export interface RWISnapshot {
  score: number;              // 0–100
  window_status: RWIWindowStatus;
  components: {
    decision_fatigue_estimate: number;
    validation_recency: number;
    identity_momentum: number;
    friction_saturation: number;
  };
  prospect_id: string;
}

// ================================================================== //
//  BAR STATE                                                           //
// ================================================================== //

export type BarTrend = 'rising' | 'falling' | 'stable';

export interface BarState {
  hook_score: number;         // 0–100 — matches Python BarState.hook_score
  close_score: number;        // 0–100 — matches Python BarState.close_score
  hook_trend: BarTrend;
  close_trend: BarTrend;
}

// ================================================================== //
//  DIALOG OPTIONS                                                      //
// ================================================================== //

export interface DialogOption {
  core_approach: string;
  base_language: string;
  trigger_phrase: string;
  base_probability: number;   // 0–100
}

export interface SelectionResult {
  moment_type: string;
  option_a: DialogOption;
  option_b: DialogOption;
  option_c: DialogOption;
  was_adapted: boolean;
  is_cache_fallback: boolean;
  classification_confidence: number;  // 0.0–1.0
}

// ================================================================== //
//  PARALINGUISTIC SIGNALS (Stream B)                                   //
// ================================================================== //

export interface ParalinguisticSignals {
  // Python field names — matches paralinguistic_extractor.ParalinguisticSignals exactly
  speech_rate_delta: number;          // -1.0 (slower) to +1.0 (faster) vs baseline
  volume_level: number;               // 0.0–1.0 normalized against ambient
  pause_duration: number;             // seconds of silence after practitioner spoke
  voice_tension_index: number;        // 0.0–1.0 pitch variance + vocal fry proxy
  cadence_consistency_score: number;  // 0.0–1.0 rhythm regularity
}

// ================================================================== //
//  DIVERGENCE ALERT                                                    //
// ================================================================== //

export interface DivergenceAlert {
  active: boolean;
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  description: string;
  verbal_state: string;
  para_state: string;
  recommendation: string;
  // Backend fields (kept for compatibility)
  verbal_type?: MomentType | null;
  alert_message?: string;
  practitioner_instruction?: string;
  tension_index?: number | null;
}

// ================================================================== //
//  CONFIDENCE BADGE                                                    //
// ================================================================== //

export interface ConfidenceBadge {
  level: ConfidenceLevel;
  label: string;
  color: 'green' | 'yellow' | 'red';
}

// ================================================================== //
//  HUD STATE (full live session state — Zone 2 WebSocket payload)      //
// ================================================================== //

export interface HUDState {
  // Bars
  bars: BarState;
  // Moment
  moment_type: MomentType;
  classification_confidence: number;   // 0.0–1.0
  // Genome confidence — always present (Constraint #4)
  confidence_badge: ConfidenceBadge;
  // RWI live
  rwi_live: {
    score: number;
    window_status: RWIWindowStatus;
  };
  // Dialog selection
  selection: SelectionResult | null;
  // Paralinguistics (Stream B)
  para: ParalinguisticSignals | null;
  // Divergence alert
  divergence_alert: DivergenceAlert | null;
  // Session state
  elapsed_seconds: number;
  selected_key: 'option_a' | 'option_b' | 'option_c' | null;
  timestamp: string | null;
}

// ================================================================== //
//  PRE-SESSION SCREEN                                                  //
// ================================================================== //

export interface PsychFlag {
  flag_id: string;
  severity: 'HIGH' | 'MODERATE' | 'LOW';
  flag_type: string;
  message: string;
  recommendation: string;
}

export interface PreSessionPayload {
  session_id: string;
  prospect_id: string;
  prospect_name: string;
  role: string;
  company: string;
  confidence_badge: ConfidenceBadge;
  rwi: RWISnapshot;
  psych_flags: PsychFlag[];
  unacknowledged_flag_ids: string[];
  can_start: boolean;
  cache_built: boolean;
  genome_validity_score: string;
  ecological_validity_score: string;
  summary: string;
}

// ================================================================== //
//  MUTATION REVIEW (ZONE 3)                                            //
// ================================================================== //

export interface MutationCandidate {
  candidate_id: string;
  prospect_id: string;
  trait_name: string;
  direction: 'increase' | 'decrease' | 'recalibrate';
  strength: MutationStrength;
  rationale: string;
  observation_count: number;
  is_coherence_tension: boolean;
  // Raw score fields (from backend MutationCandidate)
  current_score?: number;
  suggested_delta?: number;
  suggested_new_score?: number;
  evidence?: string[];
}

export interface MutationReviewPayload {
  session_id: string;
  mutation_candidates: MutationCandidate[];
  analyzed_at: string;
  is_fallback: boolean;
}

export type MutationDecision = 'confirm' | 'dismiss';

// ================================================================== //
//  MIRROR REPORT (ZONE 3 — POST-SESSION ONLY)                         //
// ================================================================== //

export interface MirrorReportPayload {
  session_id: string;
  practitioner_id: string;
  // 4 observations (flat — renderer responsibility)
  what_worked: string;
  what_didnt: string;
  pattern_detected: string;
  next_session_focus: string;
  // Session summary stats
  session_duration_min: number;
  moment_count: number;
  option_choices: number;
  divergence_count: number;
  // Practitioner profile excerpt
  strengths: string[];
  development_areas: string[];
  // Backend nested fields (kept for compatibility)
  observations?: {
    signature_strength: string;
    blind_spot: string;
    instinct_ratio: string;
    pressure_signature: string;
  };
  profile_context?: {
    session_count: number;
    strengths: string[];
    development_areas: string[];
    override_success_rate: number;
    missed_window_rate: number;
    close_threshold_instinct: number;
  };
  generated_at?: string;
  is_fallback?: boolean;
}

// ================================================================== //
//  NAVIGATION TYPES                                                    //
// ================================================================== //

export type RootStackParamList = {
  PreSession: { prospectId?: string } | undefined;
  LiveHUD: { sessionId: string };
  MutationReview: { sessionId: string };
  MirrorReport: { sessionId: string };
};
