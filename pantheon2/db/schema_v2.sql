-- ============================================================
-- Pantheon 2.0 — Supabase Schema Migration
-- Run once in Supabase Dashboard → SQL Editor
--
-- Creates NEW v2 tables. Does NOT modify agent_genomes (v1).
-- v1 and v2 coexist in the same Supabase project.
-- ============================================================

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- prospect_genomes: Individual prospect profiles (v2)
-- Separate from agent_genomes which holds v1 demographic archetypes
-- ============================================================
CREATE TABLE IF NOT EXISTS prospect_genomes (
    genome_id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prospect_id         TEXT NOT NULL,
    confidence          TEXT NOT NULL CHECK (confidence IN ('HIGH', 'MEDIUM', 'LOW')),

    -- Cluster A: OCEAN-derived
    openness                    INTEGER NOT NULL CHECK (openness BETWEEN 1 AND 100),
    conscientiousness           INTEGER NOT NULL CHECK (conscientiousness BETWEEN 1 AND 100),
    extraversion                INTEGER NOT NULL CHECK (extraversion BETWEEN 1 AND 100),
    agreeableness               INTEGER NOT NULL CHECK (agreeableness BETWEEN 1 AND 100),
    neuroticism                 INTEGER NOT NULL CHECK (neuroticism BETWEEN 1 AND 100),

    -- Cluster B: Behavioral and Cultural
    communication_style         INTEGER NOT NULL CHECK (communication_style BETWEEN 1 AND 100),
    decision_making             INTEGER NOT NULL CHECK (decision_making BETWEEN 1 AND 100),
    brand_relationship          INTEGER NOT NULL CHECK (brand_relationship BETWEEN 1 AND 100),
    influence_susceptibility    INTEGER NOT NULL CHECK (influence_susceptibility BETWEEN 1 AND 100),
    emotional_expression        INTEGER NOT NULL CHECK (emotional_expression BETWEEN 1 AND 100),
    conflict_behavior           INTEGER NOT NULL CHECK (conflict_behavior BETWEEN 1 AND 100),
    literacy_and_articulation   INTEGER NOT NULL CHECK (literacy_and_articulation BETWEEN 1 AND 100),
    socioeconomic_friction      INTEGER NOT NULL CHECK (socioeconomic_friction BETWEEN 1 AND 100),

    -- Cluster C: Cognitive Architecture (new in v2)
    identity_fusion             INTEGER NOT NULL CHECK (identity_fusion BETWEEN 1 AND 100),
    chronesthesia_capacity      INTEGER NOT NULL CHECK (chronesthesia_capacity BETWEEN 1 AND 100),
    tom_self_awareness          INTEGER NOT NULL CHECK (tom_self_awareness BETWEEN 1 AND 100),
    tom_social_modeling         INTEGER NOT NULL CHECK (tom_social_modeling BETWEEN 1 AND 100),
    executive_flexibility       INTEGER NOT NULL CHECK (executive_flexibility BETWEEN 1 AND 100),

    -- Metadata
    formation_invariants        JSONB DEFAULT '[]'::jsonb,
    last_scraped_at             TIMESTAMPTZ,
    created_at                  TIMESTAMPTZ DEFAULT now(),
    updated_at                  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_prospect_genomes_prospect_id ON prospect_genomes(prospect_id);
CREATE INDEX IF NOT EXISTS idx_prospect_genomes_created_at ON prospect_genomes(created_at DESC);

-- ============================================================
-- prospect_mutation_log: Confirmed genome mutations (gate-approved)
-- ============================================================
CREATE TABLE IF NOT EXISTS prospect_mutation_log (
    log_id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prospect_id             TEXT NOT NULL,
    trait_name              TEXT NOT NULL,
    old_score               INTEGER NOT NULL,
    new_score               INTEGER NOT NULL,
    delta                   INTEGER NOT NULL,
    confirmed_at            TIMESTAMPTZ DEFAULT now(),
    confirmed_by            TEXT NOT NULL,    -- practitioner_id
    evidence_summary        TEXT NOT NULL,
    gate_observations_count INTEGER NOT NULL,
    gate_contexts_count     INTEGER NOT NULL,
    gate_day_span           INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_mutation_log_prospect_id ON prospect_mutation_log(prospect_id);
CREATE INDEX IF NOT EXISTS idx_mutation_log_confirmed_at ON prospect_mutation_log(confirmed_at DESC);

-- ============================================================
-- sessions: Session lifecycle records
-- ============================================================
CREATE TABLE IF NOT EXISTS sessions (
    session_id          TEXT PRIMARY KEY,
    practitioner_id     TEXT NOT NULL,
    prospect_id         TEXT NOT NULL,
    genome_confidence   TEXT NOT NULL CHECK (genome_confidence IN ('HIGH', 'MEDIUM', 'LOW')),
    rwi_at_start        INTEGER NOT NULL CHECK (rwi_at_start BETWEEN 0 AND 100),
    outcome             TEXT CHECK (outcome IN ('close_yes', 'close_no', 'follow_up', 'incomplete')),
    opened_at           TIMESTAMPTZ DEFAULT now(),
    closed_at           TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_sessions_practitioner ON sessions(practitioner_id);
CREATE INDEX IF NOT EXISTS idx_sessions_prospect ON sessions(prospect_id);

-- ============================================================
-- session_events: Moment-level events during live session (Zone 2)
-- ============================================================
CREATE TABLE IF NOT EXISTS session_events (
    event_id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id          TEXT NOT NULL REFERENCES sessions(session_id),
    event_type          TEXT NOT NULL,   -- moment_change | option_chosen | snapshot | divergence_alert
    event_timestamp     TIMESTAMPTZ DEFAULT now(),
    moment_type         TEXT,
    option_chosen       TEXT,
    hook_bar            INTEGER CHECK (hook_bar BETWEEN 0 AND 100),
    close_bar           INTEGER CHECK (close_bar BETWEEN 0 AND 100),
    rwi_live            INTEGER CHECK (rwi_live BETWEEN 0 AND 100),
    notes               TEXT
);

CREATE INDEX IF NOT EXISTS idx_session_events_session_id ON session_events(session_id);
CREATE INDEX IF NOT EXISTS idx_session_events_timestamp ON session_events(event_timestamp);

-- ============================================================
-- paralinguistic_snapshots: 30-second audio feature snapshots (Zone 2)
-- ============================================================
CREATE TABLE IF NOT EXISTS paralinguistic_snapshots (
    snapshot_id                 UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id                  TEXT NOT NULL REFERENCES sessions(session_id),
    captured_at                 TIMESTAMPTZ DEFAULT now(),
    speech_rate_delta           FLOAT DEFAULT 0.0,
    volume_level                FLOAT DEFAULT 0.5,
    pause_duration_last         FLOAT DEFAULT 0.0,
    voice_tension_index         FLOAT DEFAULT 0.0,
    cadence_consistency_score   FLOAT DEFAULT 1.0,
    baseline_established        BOOLEAN DEFAULT FALSE,
    divergence_active           BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_para_snapshots_session_id ON paralinguistic_snapshots(session_id);

-- ============================================================
-- practitioner_profiles: Practitioner self-profile (accumulates from session 1)
-- ============================================================
CREATE TABLE IF NOT EXISTS practitioner_profiles (
    profile_id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    practitioner_id             TEXT UNIQUE NOT NULL,
    pressure_response_style     INTEGER DEFAULT 50 CHECK (pressure_response_style BETWEEN 1 AND 100),
    recovery_velocity           INTEGER DEFAULT 50 CHECK (recovery_velocity BETWEEN 1 AND 100),
    freeze_threshold            INTEGER DEFAULT 50 CHECK (freeze_threshold BETWEEN 1 AND 100),
    close_threshold_instinct    INTEGER DEFAULT 50 CHECK (close_threshold_instinct BETWEEN 1 AND 100),
    missed_window_rate          FLOAT DEFAULT 0.0,
    conflict_engagement         INTEGER DEFAULT 50 CHECK (conflict_engagement BETWEEN 1 AND 100),
    silence_tolerance           INTEGER DEFAULT 50 CHECK (silence_tolerance BETWEEN 1 AND 100),
    override_success_rate       FLOAT DEFAULT 0.0,
    sessions_count              INTEGER DEFAULT 0,
    created_at                  TIMESTAMPTZ DEFAULT now(),
    updated_at                  TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- Verify
-- ============================================================
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN (
    'prospect_genomes', 'prospect_mutation_log', 'sessions',
    'session_events', 'paralinguistic_snapshots', 'practitioner_profiles'
);
