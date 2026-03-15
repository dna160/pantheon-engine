import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv('pantheon.env', override=True)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# ─────────────────────────────────────────────────────────────────────────────
# FULL CREATE TABLE (fresh install — use if table does not exist yet)
# ─────────────────────────────────────────────────────────────────────────────
SQL_CREATE = """
-- Enable UUID generation if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS agent_genomes (
    -- ── Identity ────────────────────────────────────────────────────────────
    id                      UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at              TIMESTAMP   DEFAULT now(),
    target_demographic      VARCHAR,
    age                     INTEGER,
    region                  VARCHAR,

    -- ── Cultural & Religious Profile ─────────────────────────────────────────
    ethnicity               VARCHAR,    -- e.g. 'Batak Toba', 'Chinese-Indonesian', 'African American'
    cultural_primary        VARCHAR,    -- primary cultural identity (usually same as ethnicity)
    cultural_secondary      VARCHAR,    -- secondary cultural identity if bicultural (nullable)
    religion_of_origin      VARCHAR,    -- religion raised in, e.g. 'Protestant', 'Islam (Devout)'
    current_religion        VARCHAR,    -- religion now (may differ if converted)
    religiosity             INT,        -- 1=atheist/secular, 100=fundamentalist devout
    partner_culture         VARCHAR,    -- nullable — partner ethnicity if intercultural relationship
    partner_religion        VARCHAR,    -- nullable — partner religion if differs from agent

    -- ── Personality Genome (1–100 continuous sliders) ─────────────────────────
    -- Low ↔ High
    openness                INT,        -- Rigidly traditional ↔ Radically curious
    conscientiousness       INT,        -- Chaotically spontaneous ↔ Obsessively structured
    extraversion            INT,        -- Deeply internal ↔ Compulsively social
    agreeableness           INT,        -- Confrontational ↔ Peace-seeking
    neuroticism             INT,        -- Unshakably calm ↔ Chronically anxious
    communication_style     INT,        -- Blunt/terse ↔ Diplomatic/verbose
    decision_making         INT,        -- Gut instinct ↔ Analytical paralysis
    brand_relationship      INT,        -- Skeptical/anti-brand ↔ Brand-loyal evangelist
    influence_susceptibility INT,       -- Immune to social proof ↔ Heavily peer-influenced
    emotional_expression    INT,        -- Stoic/reserved ↔ Explosive/transparent
    conflict_behavior       INT,        -- Conflict-avoidant ↔ Confrontational
    literacy_and_articulation INT,      -- 1=barely literate, 100=eloquent/highly educated
    socioeconomic_friction  INT,        -- 1=comfortable trajectory, 100=severe systemic barriers

    -- ── Cognitive Architecture (1–100 continuous sliders) ───────────────────
    identity_fusion         INT DEFAULT 50,  -- 1=pure individualist, 100=visceral group oneness
    chronesthesia_capacity  INT DEFAULT 50,  -- 1=present-only thinker, 100=vivid mental time traveler
    tom_self_awareness      INT DEFAULT 50,  -- 1=blind to own states, 100=deep self-reflection
    tom_social_modeling     INT DEFAULT 50,  -- 1=oblivious to others, 100=reads rooms perfectly
    executive_flexibility   INT DEFAULT 50,  -- 1=traits leak always, 100=can override impulses

    -- ── 100-Year Life Blueprint (JSONB) ─────────────────────────────────────
    -- Queried at runtime by agent's age to extract relevant layers
    origin_layer            JSONB,      -- Age 0–5: birth, family, attachment style
    formation_layer         JSONB,      -- Age 5–18: education, adolescence, belief formation
    independence_layer      JSONB,      -- Age 18–35: career, relationships, identity
    maturity_layer          JSONB,      -- Age 35–60: mid-life, worldview consolidation
    legacy_layer            JSONB,      -- Age 60+: mortality, technology, regrets

    -- ── Voice & Communication Profile ────────────────────────────────────────
    voice_print             JSONB,      -- vocabulary_level, filler_words, cultural_speech_markers,
                                        -- religious_language, persuasion_triggers, conflict_style

    -- ── Mutation History ─────────────────────────────────────────────────────
    -- Array of life events that shifted traits from baseline to final genome.
    -- Cultural/religious events are prepended by the seeder;
    -- Claude generates additional non-cultural life events.
    genome_mutation_log     JSONB       -- [{life_stage, event_description, trait_modifiers}]
);

-- ── Indexes ─────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_agent_genomes_demographic  ON agent_genomes(target_demographic);
CREATE INDEX IF NOT EXISTS idx_agent_genomes_age          ON agent_genomes(age);
CREATE INDEX IF NOT EXISTS idx_agent_genomes_ethnicity    ON agent_genomes(ethnicity);
CREATE INDEX IF NOT EXISTS idx_agent_genomes_religion     ON agent_genomes(current_religion);
CREATE INDEX IF NOT EXISTS idx_agent_genomes_religiosity  ON agent_genomes(religiosity);
"""

# ─────────────────────────────────────────────────────────────────────────────
# ALTER TABLE (migration — use if table already exists from old schema)
# Run each statement separately in Supabase SQL Editor if needed.
# ─────────────────────────────────────────────────────────────────────────────
SQL_MIGRATE = """
-- Cultural & Religious columns (skip any that already exist)
ALTER TABLE agent_genomes ADD COLUMN IF NOT EXISTS ethnicity               VARCHAR;
ALTER TABLE agent_genomes ADD COLUMN IF NOT EXISTS cultural_primary        VARCHAR;
ALTER TABLE agent_genomes ADD COLUMN IF NOT EXISTS cultural_secondary      VARCHAR;
ALTER TABLE agent_genomes ADD COLUMN IF NOT EXISTS religion_of_origin      VARCHAR;
ALTER TABLE agent_genomes ADD COLUMN IF NOT EXISTS current_religion        VARCHAR;
ALTER TABLE agent_genomes ADD COLUMN IF NOT EXISTS religiosity             INT;
ALTER TABLE agent_genomes ADD COLUMN IF NOT EXISTS partner_culture         VARCHAR;
ALTER TABLE agent_genomes ADD COLUMN IF NOT EXISTS partner_religion        VARCHAR;

-- New genome columns
ALTER TABLE agent_genomes ADD COLUMN IF NOT EXISTS literacy_and_articulation INT;
ALTER TABLE agent_genomes ADD COLUMN IF NOT EXISTS socioeconomic_friction   INT;

-- Mutation history
ALTER TABLE agent_genomes ADD COLUMN IF NOT EXISTS genome_mutation_log     JSONB;

-- Voice print enrichment (cultural_speech_markers + religious_language added inside existing JSONB)
-- No schema change needed — voice_print is already JSONB; just ensure seeder writes the new keys.

-- Cognitive architecture columns (v3)
ALTER TABLE agent_genomes ADD COLUMN IF NOT EXISTS identity_fusion         INT DEFAULT 50;
ALTER TABLE agent_genomes ADD COLUMN IF NOT EXISTS chronesthesia_capacity  INT DEFAULT 50;
ALTER TABLE agent_genomes ADD COLUMN IF NOT EXISTS tom_self_awareness      INT DEFAULT 50;
ALTER TABLE agent_genomes ADD COLUMN IF NOT EXISTS tom_social_modeling     INT DEFAULT 50;
ALTER TABLE agent_genomes ADD COLUMN IF NOT EXISTS executive_flexibility   INT DEFAULT 50;

-- New indexes
CREATE INDEX IF NOT EXISTS idx_agent_genomes_ethnicity   ON agent_genomes(ethnicity);
CREATE INDEX IF NOT EXISTS idx_agent_genomes_religion    ON agent_genomes(current_religion);
CREATE INDEX IF NOT EXISTS idx_agent_genomes_religiosity ON agent_genomes(religiosity);
"""


# ─────────────────────────────────────────────────────────────────────────────
# WHISPER RUNS TABLE  (Client Whisperer pipeline audit trail)
# Run in Supabase SQL Editor to create this table.
# ─────────────────────────────────────────────────────────────────────────────
SQL_WHISPER_RUNS = """
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS whisper_runs (
    id              UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at      TIMESTAMP   DEFAULT now(),
    prospect_name   VARCHAR,
    linkedin_url    TEXT,
    instagram_url   TEXT,
    product_details TEXT,
    genome_id       UUID,           -- references agent_genomes(id) (soft FK)
    strategy_result JSONB,          -- full ClientWhispererStrategy JSON
    simulated_life  TEXT            -- formatted PANTHEON blueprint string
);

CREATE INDEX IF NOT EXISTS idx_whisper_runs_created_at ON whisper_runs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_whisper_runs_prospect   ON whisper_runs(prospect_name);
"""


if __name__ == "__main__":
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("Missing SUPABASE credentials in environment variables.")
        exit(1)

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    print("=" * 80)
    print("PANTHEON — Database Schema")
    print("=" * 80)
    print()
    print("Paste one of the SQL blocks below into your Supabase Dashboard SQL Editor.")
    print()
    print("── OPTION A: Fresh install (table does not exist yet) ──────────────────────")
    print(SQL_CREATE)
    print()
    print("── OPTION B: Migration (table already exists — adds new columns only) ──────")
    print(SQL_MIGRATE)
    print()
    print("── OPTION C: Client Whisperer run history (whisper_runs table) ─────────────")
    print(SQL_WHISPER_RUNS)
    print("=" * 80)
