# PANTHEON DATABASE SCHEMA: The Immutable DNA

## Objective
Define the Supabase PostgreSQL database schema for storing the pre-generated "Immutable DNA" of the simulated human agents.

## Core Table: `agent_genomes`
This table stores the fixed psychological traits and historical blueprints of the agents. It must be optimized for rapid querying by demographic markers.

### 1. Metadata Columns (Standard SQL Types)
* `id`: UUID (Primary Key, default: `uuid_generate_v4()`)
* `created_at`: TIMESTAMP (default: `now()`)
* `target_demographic`: VARCHAR (e.g., 'Urban Millennial', 'Suburban Parent') - Indexed for fast querying.
* `age`: INTEGER
* `region`: VARCHAR

### 2. The Personality Genome (Integers 1-100)
These columns define the agent's psychological sliders.
* `openness`: INT
* `conscientiousness`: INT
* `extraversion`: INT
* `agreeableness`: INT
* `neuroticism`: INT
* `communication_style`: INT
* `decision_making`: INT
* `brand_relationship`: INT
* `influence_susceptibility`: INT
* `emotional_expression`: INT
* `conflict_behavior`: INT
* `literacy_and_articulation`: INT — 1=barely literate/inarticulate, 100=eloquent/highly educated. Dictates vocabulary, sentence complexity, and confidence in speech.
* `socioeconomic_friction`: INT — 1=minimal barriers/comfortable trajectory, 100=severe systemic barriers, crushing debt, or career stagnation. Shapes pessimism, risk-aversion, and financial decision-making.

### 3. The 100-Year Life Blueprint (JSONB Columns)
These must be stored as `JSONB` to allow for nested data extraction based on the agent's age at runtime.
* `origin_layer`: JSONB (Birth circumstances, socioeconomic start, early attachment)
* `formation_layer`: JSONB (Adolescence, education, foundational beliefs)
* `independence_layer`: JSONB (Career, financial trajectory, consumer psychology)
* `maturity_layer`: JSONB (Mid-life milestones, worldview solidification)
* `legacy_layer`: JSONB (Retirement, relationship with technology)
* `voice_print`: JSONB (Vocabulary level, filler words, persuasion triggers)
* `genome_mutation_log`: JSONB — Variable-length array of life events that mutated the Base Nature genome into the Final Genome. Each item contains:
  * `life_stage` (string enum: Origin / Formation / Independence / Maturity / Legacy)
  * `event_description` (string, max 80 chars)
  * `trait_modifiers` (object: trait_name → integer shift, e.g. `{"neuroticism": 15, "conscientiousness": -5}`)
  * An empty array `[]` is valid and means the agent had a completely stable life with no mutation events.

## Directives for the Developer Agent:
1. When generating the database initialization script, include the necessary SQL commands to create this exact table in Supabase.
2. Ensure `target_demographic` and `age` have database indexes, as the orchestration routing will query these heavily per brief.
3. When writing the Python generator script (the "Genome Builder"), use `claude-haiku-4-5-20251001` with a strict JSON system prompt to ensure the JSONB fields are richly populated and psychologically aligned with the integer-based Personality Genome.
