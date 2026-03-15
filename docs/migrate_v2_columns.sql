-- PANTHEON v2 schema migration
-- Run this once in Supabase Dashboard → SQL Editor
-- Adds the three new columns required by the updated genesis engine.

ALTER TABLE agent_genomes
  ADD COLUMN IF NOT EXISTS literacy_and_articulation INTEGER DEFAULT 50,
  ADD COLUMN IF NOT EXISTS socioeconomic_friction    INTEGER DEFAULT 50,
  ADD COLUMN IF NOT EXISTS genome_mutation_log       JSONB   DEFAULT '[]'::jsonb;

-- Verify
SELECT column_name, data_type, column_default
FROM   information_schema.columns
WHERE  table_name = 'agent_genomes'
   AND column_name IN (
       'literacy_and_articulation',
       'socioeconomic_friction',
       'genome_mutation_log'
   );
