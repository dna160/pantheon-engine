"""
PANTHEON Cultural & Religious Genome Engine
============================================
Statistically grounded cultural, ethnic, and religious profile generation.

Conversion probabilities derived from:
  - Pew Research Center (2015, 2021 Religious Landscape Studies)
  - Indonesian Ministry of Religious Affairs demographic data
  - Gallup World Religion surveys
  - Academic literature on interfaith marriage and religious switching

Key design principles:
  1. Pre-determines all cultural/religious FACTS in Python before Claude is called
  2. Applies culturally authentic modifiers to the integer genome
  3. Generates mutation_log entries for all cultural/religious life events
  4. Produces a rich context block for injection into the Claude prompt
"""

import random
from typing import Optional

# ─────────────────────────────────────────────────────────────────────────────
# SYSTEM PROMPT — shared across all Genesis Builder seed scripts
# ─────────────────────────────────────────────────────────────────────────────
GENESIS_SYSTEM_PROMPT = """You are the PANTHEON Genesis Builder.
You ALWAYS respond with ONLY valid JSON — no markdown, no commentary, no code fences.

Your JSON must conform EXACTLY to this structure:
{
  "origin_layer": {
    "summary": "string",
    "key_events": ["string", "string", "string"],
    "psychological_impact": "string"
  },
  "formation_layer": {
    "summary": "string",
    "key_events": ["string", "string", "string"],
    "psychological_impact": "string"
  },
  "independence_layer": {
    "summary": "string",
    "key_events": ["string", "string", "string"],
    "psychological_impact": "string"
  },
  "maturity_layer": {
    "summary": "string",
    "key_events": ["string", "string", "string"],
    "psychological_impact": "string"
  },
  "legacy_layer": {
    "summary": "string",
    "key_events": ["string", "string", "string"],
    "psychological_impact": "string"
  },
  "voice_print": {
    "vocabulary_level": "string",
    "filler_words": ["string", "string", "string"],
    "cultural_speech_markers": ["string", "string"],
    "religious_language": ["string", "string"],
    "persuasion_triggers": ["string", "string", "string"],
    "conflict_style": "string"
  },
  "genome_mutation_log": [
    {
      "life_stage": "string (Origin|Formation|Independence|Maturity|Legacy)",
      "event_description": "string",
      "trait_modifiers": { "trait_name": integer_delta }
    }
  ]
}

IMPORTANT RULES FOR genome_mutation_log:
- Include 3 to 6 NON-CULTURAL life events only (cultural and religious events are already provided)
- Examples: parental divorce, bankruptcy, serious illness, career failure or breakthrough, academic rejection, addiction and recovery, loss of a parent, migration, trauma, betrayal
- trait_modifiers should reference only: openness, conscientiousness, extraversion, agreeableness, neuroticism, communication_style, decision_making, brand_relationship, influence_susceptibility, emotional_expression, conflict_behavior, identity_fusion, chronesthesia_capacity, tom_self_awareness, tom_social_modeling, executive_flexibility
- Deltas should be between -25 and +25 and directionally justify the genome scores
- The genome scores represent the FINAL state — your mutation log explains HOW they got there

IMPORTANT RULES FOR legacy_layer:
- legacy_layer represents the agent's CURRENT aspirational projection — what they imagine their future looks like right now — NOT a fixed destiny
- Frame it as "what they currently believe their trajectory is" — this projection may shift during simulation
- A 28-year-old's legacy_layer should reflect naive optimism or anxiety about the future, not omniscient certainty

IMPORTANT RULES FOR voice_print:
- cultural_speech_markers: dialect markers, code-switching patterns, borrowed words (e.g., "lah bah" for Batak, "insyaAllah" for Muslims, "aiyah" for Chinese-Indonesian, etc.)
- religious_language: faith-specific expressions, invocations, casual religious references (e.g., "Puji Tuhan", "Praise God", "may God bless", "amin", etc.)
- If the agent is secular/atheist, religious_language should be empty or contain ironic/vestigial references

All life layer narratives MUST be internally consistent with the cultural and religious profile provided in the prompt."""


# ─────────────────────────────────────────────────────────────────────────────
# ETHNICITY POOLS BY REGION
# (ethnicity_label, sampling_weight)
# ─────────────────────────────────────────────────────────────────────────────
ETHNICITY_POOLS: dict[str, list[tuple[str, float]]] = {
    "Medan, Indonesia": [
        ("Batak Toba",         0.22),
        ("Batak Karo",         0.10),
        ("Batak Simalungun",   0.05),
        ("Javanese",           0.12),
        ("Chinese-Indonesian", 0.16),
        ("Acehnese",           0.08),
        ("Minangkabau",        0.09),
        ("Malay Deli",         0.10),
        ("Nias",               0.04),
        ("Mixed Ethnic",       0.04),
    ],
    "North America": [
        ("White non-Hispanic",  0.57),
        ("African American",    0.13),
        ("Hispanic/Latino",     0.19),
        ("Asian American",      0.06),
        ("Mixed/Multiracial",   0.05),
    ],
    "Singapore": [
        ("Chinese Singaporean",  0.74),
        ("Malay Singaporean",    0.13),
        ("Indian Singaporean",   0.09),
        ("Eurasian/Peranakan",   0.04),
    ],
    "Japan": [
        ("Japanese",             0.92),
        ("Zainichi Korean",      0.03),
        ("Chinese-Japanese",     0.02),
        ("Mixed/Hāfu",           0.03),
    ],
}


# ─────────────────────────────────────────────────────────────────────────────
# RELIGION DISTRIBUTION BY ETHNICITY
# (religion_label, weight)
# ─────────────────────────────────────────────────────────────────────────────
RELIGION_BY_ETHNICITY: dict[str, list[tuple[str, float]]] = {
    # ── Medan, Indonesia ──────────────────────────────────────────────────────
    "Batak Toba":        [("Protestant",        0.80), ("Catholic",       0.15), ("Islam",               0.05)],
    "Batak Karo":        [("Protestant",        0.70), ("Islam",          0.25), ("Catholic",            0.05)],
    "Batak Simalungun":  [("Protestant",        0.75), ("Islam",          0.18), ("Catholic",            0.07)],
    "Javanese":          [("Islam (Nominal)",   0.52), ("Islam (Devout)", 0.38), ("Protestant",          0.05), ("Catholic", 0.03), ("Hindu/Kejawen", 0.02)],
    "Chinese-Indonesian":[("Protestant",        0.38), ("Catholic",       0.22), ("Buddhist/Taoist",     0.30), ("None/Secular", 0.08), ("Islam", 0.02)],
    "Acehnese":          [("Islam (Devout)",    0.96), ("Islam (Nominal)",0.04)],
    "Minangkabau":       [("Islam (Devout)",    0.93), ("Islam (Nominal)",0.07)],
    "Malay Deli":        [("Islam (Devout)",    0.88), ("Islam (Nominal)",0.12)],
    "Nias":              [("Protestant",        0.65), ("Catholic",       0.18), ("Islam",               0.17)],
    "Mixed Ethnic":      [("Protestant",        0.30), ("Catholic",       0.20), ("Islam (Devout)",      0.25), ("Islam (Nominal)", 0.10), ("Buddhist/Taoist", 0.10), ("None/Secular", 0.05)],
    # ── North America ─────────────────────────────────────────────────────────
    "White non-Hispanic":[("Protestant",        0.38), ("Catholic",       0.22), ("None/Agnostic",       0.26), ("Atheist", 0.07), ("Jewish", 0.04), ("Other", 0.03)],
    "African American":  [("Protestant",        0.72), ("Catholic",       0.08), ("Islam",               0.09), ("None/Agnostic", 0.09), ("Other", 0.02)],
    "Hispanic/Latino":   [("Catholic",          0.58), ("Protestant",     0.22), ("None/Agnostic",       0.17), ("Other", 0.03)],
    "Asian American":    [("Protestant",        0.26), ("Catholic",       0.13), ("Buddhist",            0.15), ("Hindu", 0.10), ("None/Agnostic", 0.26), ("Atheist", 0.06), ("Other", 0.04)],
    "Mixed/Multiracial": [("Protestant",        0.28), ("Catholic",       0.18), ("None/Agnostic",       0.30), ("Atheist", 0.10), ("Buddhist", 0.08), ("Other", 0.06)],
    # ── Singapore ─────────────────────────────────────────────────────────────
    # Source: Singapore Department of Statistics (Census 2020), upper-middle skew applied
    "Chinese Singaporean": [("Buddhist/Taoist",  0.40), ("None/Secular",   0.22), ("Protestant",   0.20),
                             ("Catholic",         0.10), ("None/Agnostic",  0.08)],
    "Malay Singaporean":   [("Islam (Devout)",    0.68), ("Islam (Nominal)", 0.32)],
    "Indian Singaporean":  [("Hindu",             0.52), ("Islam",           0.24), ("Protestant",   0.12),
                             ("Catholic",         0.07), ("None/Secular",    0.05)],
    "Eurasian/Peranakan":  [("Protestant",        0.44), ("Catholic",        0.32), ("None/Secular", 0.14),
                             ("Buddhist/Taoist",  0.10)],
    # ── Japan ─────────────────────────────────────────────────────────────────
    # Source: NHK Survey 2018, Japan General Social Survey — corporate cohort skews secular
    # Most Japanese practice Shinto/Buddhist syncretically without formal religious identity
    "Japanese":            [("None/Secular",     0.40), ("Buddhist/Taoist",  0.35), ("Shinto/Syncretic", 0.16),
                             ("Protestant",       0.03), ("Catholic",         0.02), ("New Religion",     0.04)],
    "Zainichi Korean":     [("None/Secular",     0.30), ("Buddhist/Taoist",  0.30), ("Protestant",       0.25),
                             ("Catholic",         0.10), ("None/Agnostic",    0.05)],
    "Chinese-Japanese":    [("None/Secular",     0.35), ("Buddhist/Taoist",  0.45), ("Protestant",       0.10),
                             ("Catholic",         0.05), ("None/Agnostic",    0.05)],
    "Mixed/Hāfu":          [("None/Secular",     0.38), ("Buddhist/Taoist",  0.28), ("Protestant",       0.18),
                             ("Catholic",         0.10), ("None/Agnostic",    0.06)],
}


# ─────────────────────────────────────────────────────────────────────────────
# BASE RELIGIOSITY RANGES  (1 = atheist/fully secular, 100 = fundamentalist)
# ─────────────────────────────────────────────────────────────────────────────
RELIGIOSITY_RANGES: dict[str, tuple[int, int]] = {
    "Islam (Devout)":   (62, 96),
    "Islam (Nominal)":  (14, 48),
    "Islam":            (35, 82),
    "Protestant":       (28, 80),
    "Catholic":         (25, 78),
    "Buddhist/Taoist":  (18, 68),
    "Buddhist":         (18, 65),
    "Hindu":            (28, 78),
    "Hindu/Kejawen":    (14, 52),
    "Jewish":           (22, 74),
    "None/Agnostic":      ( 1, 22),
    "None/Secular":       ( 1, 18),
    "Atheist":            ( 1, 10),
    "Other":              (18, 60),
    "Shinto/Syncretic":   ( 8, 38),  # Cultural practice, rarely devout
    "New Religion":       (38, 82),  # Soka Gakkai, Tenrikyo — active practitioners
}


# ─────────────────────────────────────────────────────────────────────────────
# INTERCULTURAL / INTERETHNIC MARRIAGE PROBABILITY BY REGION
# Sourced from BPS (Badan Pusat Statistik) Indonesia & US Census Bureau
# ─────────────────────────────────────────────────────────────────────────────
INTERCULTURAL_MARRIAGE_PROB: dict[str, float] = {
    "Medan, Indonesia": 0.18,   # Urban Medan is ethnically very diverse
    "North America":    0.24,   # Urban millennial interracial marriage rate
    "Singapore":        0.22,   # Singapore Dept of Statistics; higher among educated upper-middle class
    "Japan":            0.06,   # Ministry of Health, Labour and Welfare — Japan's intercultural marriage rate is low
}


# ─────────────────────────────────────────────────────────────────────────────
# RELIGIOUS CONVERSION MAP
# (from_group, to_group) → lifetime probability
# Religion groups: "Islam", "Protestant", "Catholic", "Buddhist", "Hindu",
#                  "Jewish", "None/Agnostic", "Atheist", "Other"
#
# Sources: Pew 2015 "America's Changing Religious Landscape",
#          Pew 2012 "Faith in Flux", Indonesian CRCS Yogyakarta studies
# ─────────────────────────────────────────────────────────────────────────────
CONVERSION_MAP: dict[tuple[str, str], float] = {
    # ── Indonesia-specific patterns ───────────────────────────────────────────
    ("Protestant",  "Islam"):          0.07,   # Via marriage (common in Medan)
    ("Catholic",    "Islam"):          0.05,   # Via marriage
    ("Protestant",  "Catholic"):       0.07,
    ("Catholic",    "Protestant"):     0.09,
    ("Buddhist",    "Protestant"):     0.13,   # Urbanization + evangelism
    ("Buddhist",    "Catholic"):       0.06,
    ("Buddhist",    "None/Agnostic"):  0.10,
    ("Islam",       "Protestant"):     0.008,  # Rare — social and legal barriers
    ("Islam",       "Catholic"):       0.004,
    ("Protestant",  "None/Agnostic"):  0.09,   # Urban secular drift
    ("Catholic",    "None/Agnostic"):  0.07,
    # ── North American patterns ───────────────────────────────────────────────
    ("Protestant",  "None/Agnostic"):  0.28,   # Millennial deconversion wave
    ("Catholic",    "None/Agnostic"):  0.24,
    ("Protestant",  "Atheist"):        0.09,
    ("Catholic",    "Atheist"):        0.08,
    ("Protestant",  "Catholic"):       0.10,
    ("Catholic",    "Protestant"):     0.14,
    ("None/Agnostic","Protestant"):    0.05,
    ("None/Agnostic","Catholic"):      0.03,
    ("Protestant",  "Buddhist"):       0.03,
    ("Catholic",    "Buddhist"):       0.03,
    ("Protestant",  "Islam"):          0.01,
    ("Catholic",    "Islam"):          0.01,
    ("Protestant",  "Jewish"):         0.02,
    ("Jewish",      "None/Agnostic"):  0.20,
    ("Jewish",      "Protestant"):     0.08,
    ("Buddhist",    "None/Agnostic"):  0.17,
    ("Buddhist",    "Protestant"):     0.06,
    ("Hindu",       "None/Agnostic"):  0.14,
    ("Hindu",       "Protestant"):     0.05,
    ("Islam",       "None/Agnostic"):  0.06,
    ("Other",       "None/Agnostic"):  0.15,
}


# ─────────────────────────────────────────────────────────────────────────────
# PERSONALITY GENOME MODIFIERS FROM CULTURE
# Applied as deltas to randomly generated base genome scores
# ─────────────────────────────────────────────────────────────────────────────
CULTURE_MODIFIERS: dict[str, dict[str, int]] = {
    # Batak Toba: Known for direct speech, high ambition, strong marga (clan) bonds
    "Batak Toba":        {"extraversion": 12, "conflict_behavior": 10, "conscientiousness": 8,
                          "communication_style": -10, "agreeableness": -5,
                          "identity_fusion": 15, "chronesthesia_capacity": 5, "tom_self_awareness": -5,
                          "tom_social_modeling": 5, "executive_flexibility": -3},
    # Batak Karo: Slightly more reserved than Toba, egalitarian community structure
    "Batak Karo":        {"extraversion": 7,  "agreeableness": 6,  "conscientiousness": 5,
                          "identity_fusion": 12, "chronesthesia_capacity": 3, "tom_social_modeling": 4,
                          "executive_flexibility": -2},
    "Batak Simalungun":  {"extraversion": 6,  "conscientiousness": 5, "agreeableness": 4,
                          "identity_fusion": 10, "chronesthesia_capacity": 3, "tom_social_modeling": 3},
    # Javanese: Collectivist, indirect communication, strong face-saving instinct (halus culture)
    "Javanese":          {"agreeableness": 14, "conflict_behavior": -14, "emotional_expression": -10,
                          "communication_style": 12, "decision_making": -6,
                          "identity_fusion": 10, "chronesthesia_capacity": 8, "tom_self_awareness": 5,
                          "tom_social_modeling": 18, "executive_flexibility": 12},
    # Chinese-Indonesian: Business-oriented, high discipline, emotional restraint, mianzi/guanxi-driven
    "Chinese-Indonesian":{"conscientiousness": 14, "decision_making": 10, "emotional_expression": -12,
                          "brand_relationship": 10, "conflict_behavior": -6,
                          "identity_fusion": 12, "chronesthesia_capacity": 12, "tom_self_awareness": 8,
                          "tom_social_modeling": 14, "executive_flexibility": 14},
    # Acehnese: Deeply Islamic, conservative, strong ummah cohesion
    "Acehnese":          {"conscientiousness": 12, "agreeableness": 8, "openness": -12,
                          "conflict_behavior": -8, "influence_susceptibility": 6,
                          "identity_fusion": 18, "chronesthesia_capacity": 10, "tom_self_awareness": -5,
                          "tom_social_modeling": 8, "executive_flexibility": 5},
    # Minangkabau: Matrilineal clan system, entrepreneurial (perantau culture), Islamic but merchant-minded
    "Minangkabau":       {"conscientiousness": 10, "decision_making": 10, "openness": -6,
                          "agreeableness": 6, "extraversion": 5,
                          "identity_fusion": 12, "chronesthesia_capacity": 8, "tom_self_awareness": 6,
                          "tom_social_modeling": 10, "executive_flexibility": 8},
    # Malay Deli: Aristocratic heritage, formal communication, protocol-conscious
    "Malay Deli":        {"agreeableness": 10, "communication_style": 10, "conflict_behavior": -10,
                          "emotional_expression": -8,
                          "identity_fusion": 14, "chronesthesia_capacity": 6, "tom_self_awareness": 4,
                          "tom_social_modeling": 14, "executive_flexibility": 10},
    # Nias: Historically warrior culture, migration challenges, resilience
    "Nias":              {"conscientiousness": 7, "extraversion": 5, "neuroticism": 5,
                          "identity_fusion": 10, "chronesthesia_capacity": -3, "tom_self_awareness": -3,
                          "tom_social_modeling": 3, "executive_flexibility": -2},
    "Mixed Ethnic":      {"openness": 12, "agreeableness": 5, "neuroticism": 6,
                          "identity_fusion": -5, "chronesthesia_capacity": 5, "tom_self_awareness": 10,
                          "tom_social_modeling": 5, "executive_flexibility": 5},
    # ── North America ─────────────────────────────────────────────────────────
    "White non-Hispanic":    {"decision_making": 6, "openness": 5,
                              "identity_fusion": -5, "chronesthesia_capacity": 3, "tom_self_awareness": 8,
                              "tom_social_modeling": -3, "executive_flexibility": 3},
    "African American":      {"extraversion": 9, "emotional_expression": 12,
                              "agreeableness": 6, "influence_susceptibility": 6,
                              "identity_fusion": 8, "chronesthesia_capacity": 3, "tom_self_awareness": 5,
                              "tom_social_modeling": 6, "executive_flexibility": 5},
    "Hispanic/Latino":       {"agreeableness": 12, "extraversion": 9, "emotional_expression": 12,
                              "communication_style": 10, "family_orientation_proxy": 8,
                              "identity_fusion": 12, "chronesthesia_capacity": 3, "tom_self_awareness": 3,
                              "tom_social_modeling": 8, "executive_flexibility": 3},
    "Asian American":        {"conscientiousness": 14, "emotional_expression": -12,
                              "decision_making": 8, "conflict_behavior": -9, "brand_relationship": 7,
                              "identity_fusion": 8, "chronesthesia_capacity": 10, "tom_self_awareness": 6,
                              "tom_social_modeling": 12, "executive_flexibility": 10},
    "Mixed/Multiracial":     {"openness": 14, "neuroticism": 9,
                              "identity_fusion": -3, "chronesthesia_capacity": 5, "tom_self_awareness": 12,
                              "tom_social_modeling": 5, "executive_flexibility": 5},
    # ── Singapore ─────────────────────────────────────────────────────────────
    # Chinese Singaporean: Kiasu (fear of losing out), high discipline, brand-status conscious, face-saving
    "Chinese Singaporean": {"conscientiousness": 16, "brand_relationship": 14, "decision_making": 10,
                             "emotional_expression": -14, "conflict_behavior": -8, "openness": -5,
                             "identity_fusion": 10, "chronesthesia_capacity": 14, "tom_self_awareness": 8,
                             "tom_social_modeling": 16, "executive_flexibility": 16},
    # Malay Singaporean: Collectivist, strong community bonds, indirect communication, religiously grounded
    "Malay Singaporean":   {"agreeableness": 14, "emotional_expression": 8, "conflict_behavior": -10,
                             "communication_style": 9, "influence_susceptibility": 7,
                             "identity_fusion": 14, "chronesthesia_capacity": 5, "tom_self_awareness": 3,
                             "tom_social_modeling": 10, "executive_flexibility": 8},
    # Indian Singaporean: Professionally driven, verbally direct, family-achievement oriented
    "Indian Singaporean":  {"conscientiousness": 12, "extraversion": 8, "communication_style": 6,
                             "decision_making": 8, "brand_relationship": 6,
                             "identity_fusion": 10, "chronesthesia_capacity": 10, "tom_self_awareness": 8,
                             "tom_social_modeling": 12, "executive_flexibility": 12},
    # Eurasian/Peranakan: Bicultural fluency, direct English-first communication, socially liberal
    "Eurasian/Peranakan":  {"openness": 12, "extraversion": 8, "communication_style": -5,
                             "agreeableness": 5, "emotional_expression": 6,
                             "identity_fusion": -3, "chronesthesia_capacity": 8, "tom_self_awareness": 10,
                             "tom_social_modeling": 8, "executive_flexibility": 10},
    # ── Japan ─────────────────────────────────────────────────────────────────
    # Japanese (Corporate Salaryman): tatemae/honne duality, wa (harmony), keigo (formal register),
    # kaisha (company) identity, nemawashi/ringi consensus, karoshi pressure, extreme social radar
    "Japanese":            {"conscientiousness": 18, "emotional_expression": -18, "conflict_behavior": -14,
                             "agreeableness": 12, "communication_style": 14, "decision_making": -10,
                             "brand_relationship": 12, "neuroticism": 8, "openness": -10,
                             "identity_fusion": 16, "chronesthesia_capacity": 8, "tom_self_awareness": 6,
                             "tom_social_modeling": 20, "executive_flexibility": -12},
    # Zainichi Korean: minority identity complexity, bicultural code-switching, higher openness via marginality
    "Zainichi Korean":     {"conscientiousness": 12, "neuroticism": 12, "openness": 8,
                             "emotional_expression": -8, "conflict_behavior": -6,
                             "identity_fusion": 6, "chronesthesia_capacity": 6, "tom_self_awareness": 12,
                             "tom_social_modeling": 14, "executive_flexibility": 6},
    # Chinese-Japanese: hybrid discipline + emotional restraint + brand consciousness
    "Chinese-Japanese":    {"conscientiousness": 16, "emotional_expression": -14, "brand_relationship": 14,
                             "decision_making": 6, "conflict_behavior": -8,
                             "identity_fusion": 10, "chronesthesia_capacity": 10, "tom_self_awareness": 8,
                             "tom_social_modeling": 16, "executive_flexibility": 8},
    # Mixed/Hāfu: identity negotiation, higher openness, some social friction in mono-ethnic workplace
    "Mixed/Hāfu":          {"openness": 14, "neuroticism": 10, "emotional_expression": -6,
                             "agreeableness": 6, "communication_style": 8,
                             "identity_fusion": -6, "chronesthesia_capacity": 8, "tom_self_awareness": 14,
                             "tom_social_modeling": 10, "executive_flexibility": 8},
}


# ─────────────────────────────────────────────────────────────────────────────
# GENOME MODIFIERS FROM RELIGIOSITY LEVEL
# Applied if religiosity >= 60 (devout) or <= 28 (secular)
# ─────────────────────────────────────────────────────────────────────────────
RELIGIOSITY_MODIFIERS: dict[str, dict[str, int]] = {
    "devout":  {"conscientiousness": 13, "agreeableness": 9, "openness": -13,
                "neuroticism": -8,  "decision_making": -6, "influence_susceptibility": 6,
                "identity_fusion": 12, "chronesthesia_capacity": 10, "tom_social_modeling": 5,
                "executive_flexibility": 8},
    "secular": {"openness": 13, "conscientiousness": -6, "decision_making": 9,
                "influence_susceptibility": -6, "neuroticism": 5,
                "identity_fusion": -8, "chronesthesia_capacity": -3, "tom_self_awareness": 8,
                "executive_flexibility": 3},
}


# ─────────────────────────────────────────────────────────────────────────────
# INTERCULTURAL MARRIAGE GENOME MODIFIERS
# ─────────────────────────────────────────────────────────────────────────────
INTERCULTURAL_MARRIAGE_MODIFIERS: dict[str, int] = {
    "openness": 16,
    "neuroticism": 9,
    "agreeableness": 6,
    "communication_style": 8,
    "identity_fusion": -5,
    "tom_social_modeling": 6,
    "executive_flexibility": 5,
}


# ─────────────────────────────────────────────────────────────────────────────
# CONVERSION TYPE GENOME MODIFIERS
# ─────────────────────────────────────────────────────────────────────────────
CONVERSION_MODIFIERS: dict[str, dict[str, int]] = {
    # Gradual loss of faith; urbanization and education eroding belief
    "secular_drift":               {"openness": 18, "conscientiousness": -8,
                                    "influence_susceptibility": -6, "neuroticism": 7,
                                    "identity_fusion": -10, "tom_self_awareness": 8},
    # Deepening commitment; revival or community-driven transformation
    "to_devout":                   {"conscientiousness": 16, "openness": -16,
                                    "agreeableness": 10, "neuroticism": -9, "influence_susceptibility": 8,
                                    "identity_fusion": 14, "executive_flexibility": 6},
    # Conversion to satisfy marriage requirement — often nominal, identity-conflicted
    "interfaith_marriage_pressure":{"neuroticism": 22, "openness": 9, "agreeableness": -6,
                                    "conscientiousness": 5, "emotional_expression": 8,
                                    "identity_fusion": -6, "tom_social_modeling": 8,
                                    "executive_flexibility": 5},
    # Authentic spiritual seeking that found a new home
    "genuine_conversion":          {"conscientiousness": 11, "openness": -11,
                                    "agreeableness": 9, "neuroticism": -13,
                                    "identity_fusion": 8, "chronesthesia_capacity": 6},
}


# ─────────────────────────────────────────────────────────────────────────────
# SOCIOECONOMIC FRICTION RANGES BY ETHNICITY
# (lo, hi) — 1=comfortable/privileged trajectory, 100=severe systemic barriers
# ─────────────────────────────────────────────────────────────────────────────
SOCIOECONOMIC_FRICTION_RANGES: dict[str, tuple[int, int]] = {
    "Batak Toba":         (20, 60),  # Strong work ethic, but variable wealth
    "Batak Karo":         (25, 65),
    "Batak Simalungun":   (28, 68),
    "Javanese":           (22, 62),
    "Chinese-Indonesian": ( 5, 42),  # Family business networks, capital access
    "Acehnese":           (28, 68),
    "Minangkabau":        (18, 58),  # Perantau culture = merchant success
    "Malay Deli":         (25, 62),
    "Nias":               (35, 80),  # Often more economically marginalized
    "Mixed Ethnic":       (20, 62),
    "White non-Hispanic": (10, 55),
    "African American":   (30, 82),  # Structural/historical barriers
    "Hispanic/Latino":    (25, 75),
    "Asian American":     ( 8, 55),  # Bimodal — high achievers or recent immigrants
    "Mixed/Multiracial":  (20, 65),
    # ── Singapore (Upper Middle Class — compressed low end) ───────────────────
    "Chinese Singaporean": ( 4, 28),  # Strong family capital, meritocratic pipeline access
    "Malay Singaporean":   (12, 42),  # Some structural disadvantage; upper-middle skew reduces ceiling
    "Indian Singaporean":  ( 6, 32),  # Professional-class orientation; upper-middle cohort
    "Eurasian/Peranakan":  ( 6, 30),  # Small community, generally well-networked
    # ── Japan (Corporate Salaryman — stable income but overwork/housing pressure) ──
    "Japanese":            ( 8, 38),  # Job security high but cost of living, housing, deflation
    "Zainichi Korean":     (18, 52),  # Minority status → some hiring friction historically
    "Chinese-Japanese":    (12, 42),
    "Mixed/Hāfu":          (10, 40),  # Visible minority in mono-ethnic society
}


# ─────────────────────────────────────────────────────────────────────────────
# LITERACY & ARTICULATION RANGES BY ETHNICITY
# (lo, hi) — 1=barely literate, 100=eloquent/highly educated
# ─────────────────────────────────────────────────────────────────────────────
LITERACY_RANGES: dict[str, tuple[int, int]] = {
    "Batak Toba":         (45, 86),  # Strong educational tradition (HKBP church schools)
    "Batak Karo":         (40, 80),
    "Batak Simalungun":   (36, 76),
    "Javanese":           (34, 76),
    "Chinese-Indonesian": (55, 92),  # Intense academic focus
    "Acehnese":           (34, 72),
    "Minangkabau":        (45, 82),  # Historical scholarship tradition
    "Malay Deli":         (30, 70),
    "Nias":               (28, 64),
    "Mixed Ethnic":       (36, 76),
    "White non-Hispanic": (40, 92),
    "African American":   (35, 86),
    "Hispanic/Latino":    (30, 80),
    "Asian American":     (52, 96),
    "Mixed/Multiracial":  (36, 86),
    # ── Singapore (bilingual, high-education system; upper-middle further skewed high) ──
    "Chinese Singaporean": (68, 96),  # English-dominant, intense academic pipeline
    "Malay Singaporean":   (62, 90),  # Strong Malay-language + English education
    "Indian Singaporean":  (68, 96),  # Professional-class cohort, English-first
    "Eurasian/Peranakan":  (70, 96),  # English-native, often elite-school educated
    # ── Japan (corporate salaryman — near-universal literacy, university-educated) ──
    "Japanese":            (72, 96),  # 99% literacy, majority university-educated, strong kanji literacy
    "Zainichi Korean":     (68, 92),
    "Chinese-Japanese":    (70, 94),
    "Mixed/Hāfu":          (68, 94),
}


# ─────────────────────────────────────────────────────────────────────────────
# BASE GENOME GENERATION
# Gaussian distribution with trait covariance — replaces flat random.randint()
# ─────────────────────────────────────────────────────────────────────────────

def _gauss_trait(mu: float = 50.0, sigma: float = 15.0) -> int:
    """Generate a single trait score from a normal distribution, clamped [1, 100]."""
    return max(1, min(100, int(random.gauss(mu, sigma))))


def _correlated_trait(anchor: int, r: float, mu: float = 50.0, sigma: float = 15.0) -> int:
    """
    Generate a trait correlated with an anchor trait.

    Uses a simplified linear model combining centered random normal distributions.
    The sign of r controls positive vs negative correlation.
    """
    noise = random.gauss(mu, sigma)
    # Center both components around mu before applying the correlation multiplier
    blended = (anchor - mu) * r + (noise - mu) * (1.0 - abs(r)) + mu
    return max(1, min(100, int(blended)))


def generate_base_genome() -> dict:
    """
    Generate a base personality genome using gaussian distributions with trait covariance.

    Big Five traits are generated independently from N(50, 15).
    Behavioral traits are derived with correlation to relevant Big Five anchors.
    Cognitive architecture traits are generated independently (cultural modifiers add covariance).

    Returns:
        dict of trait_name → int (1-100) for all 18 genome dimensions.
    """
    # ── Core Big Five (independent gaussian) ─────────────────────────────────
    openness          = _gauss_trait()
    conscientiousness = _gauss_trait()
    extraversion      = _gauss_trait()
    agreeableness     = _gauss_trait()
    neuroticism       = _gauss_trait()

    # ── Derived behavioral traits (correlated with Big Five anchors) ─────────
    # decision_making positively correlated with conscientiousness (r≈0.4)
    decision_making         = _correlated_trait(conscientiousness, r=0.4)
    # emotional_expression positively correlated with extraversion (r≈0.5)
    emotional_expression    = _correlated_trait(extraversion, r=0.5)
    # conflict_behavior negatively correlated with agreeableness (r≈-0.6)
    conflict_behavior       = _correlated_trait(agreeableness, r=-0.6)
    # influence_susceptibility weak positive with openness+agreeableness blend
    influence_anchor        = int(openness * 0.4 + agreeableness * 0.4 + 10)
    influence_susceptibility = _correlated_trait(influence_anchor, r=0.3)
    # communication_style, brand_relationship — independent (culturally determined)
    communication_style     = _gauss_trait()
    brand_relationship      = _gauss_trait()

    # ── Cognitive architecture (independent gaussian, cultural modifiers add covariance) ──
    identity_fusion         = _gauss_trait()
    chronesthesia_capacity  = _gauss_trait()
    tom_self_awareness      = _gauss_trait()
    tom_social_modeling     = _gauss_trait()
    executive_flexibility   = _gauss_trait()

    # ── Placeholder socioeconomic traits (overridden by apply_cultural_modifiers) ──
    literacy_and_articulation = _gauss_trait()
    socioeconomic_friction    = _gauss_trait()

    return {
        "openness":                openness,
        "conscientiousness":       conscientiousness,
        "extraversion":            extraversion,
        "agreeableness":           agreeableness,
        "neuroticism":             neuroticism,
        "communication_style":     communication_style,
        "decision_making":         decision_making,
        "brand_relationship":      brand_relationship,
        "influence_susceptibility":influence_susceptibility,
        "emotional_expression":    emotional_expression,
        "conflict_behavior":       conflict_behavior,
        "literacy_and_articulation": literacy_and_articulation,
        "socioeconomic_friction":    socioeconomic_friction,
        "identity_fusion":         identity_fusion,
        "chronesthesia_capacity":  chronesthesia_capacity,
        "tom_self_awareness":      tom_self_awareness,
        "tom_social_modeling":     tom_social_modeling,
        "executive_flexibility":   executive_flexibility,
    }


def apply_age_drift(genome: dict, age: int) -> dict:
    """
    Apply systematic age-graded personality development to a base genome.

    Based on developmental psychology research on mean-level personality changes
    across the adult lifespan (Roberts, Walton & Viechtbauer, 2006):
      - Conscientiousness increases through adulthood (+0.3/yr after 20)
      - Agreeableness increases in middle adulthood (+0.2/yr after 25)
      - Neuroticism declines in adulthood (-0.2/yr after 30)
      - Openness declines slightly in later adulthood (-0.1/yr after 35)
      - Chronesthesia (foresight) matures with experience (+0.15/yr after 25)
      - Executive flexibility peaks mid-life (inverted-U, +0.2/yr from 20, declining after 50)

    This function should be called AFTER generate_base_genome() and BEFORE
    apply_cultural_modifiers(), so that mutations act as acute deviations
    from a natural developmental curve.

    Args:
        genome: dict from generate_base_genome()
        age: agent's age in years

    Returns:
        new genome dict with age drift applied
    """
    g = genome.copy()

    # Conscientiousness: steady increase from age 20 onward
    g["conscientiousness"] = max(1, min(100,
        g["conscientiousness"] + int(max(0, age - 20) * 0.3)))

    # Agreeableness: increases from age 25 onward
    g["agreeableness"] = max(1, min(100,
        g["agreeableness"] + int(max(0, age - 25) * 0.2)))

    # Neuroticism: declines from age 30 onward
    g["neuroticism"] = max(1, min(100,
        g["neuroticism"] - int(max(0, age - 30) * 0.2)))

    # Openness: slight decline from age 35 onward
    g["openness"] = max(1, min(100,
        g["openness"] - int(max(0, age - 35) * 0.1)))

    # Chronesthesia: foresight matures with experience
    g["chronesthesia_capacity"] = max(1, min(100,
        g["chronesthesia_capacity"] + int(max(0, age - 25) * 0.15)))

    # Executive flexibility: inverted-U — peaks in middle age
    # +0.2/yr from 20 to 50, then -0.15/yr after 50
    if age <= 50:
        ef_drift = int(max(0, age - 20) * 0.2)
    else:
        ef_drift = int(30 * 0.2) - int((age - 50) * 0.15)  # peak at 50, then decline
    g["executive_flexibility"] = max(1, min(100,
        g["executive_flexibility"] + ef_drift))

    return g


# ─────────────────────────────────────────────────────────────────────────────
# INTERNAL HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _weighted_choice(pool: list[tuple[str, float]]) -> str:
    """Sample from a (label, weight) pool."""
    labels, weights = zip(*pool)
    return random.choices(labels, weights=weights, k=1)[0]


def _clamp(val: int, lo: int = 1, hi: int = 100) -> int:
    return max(lo, min(hi, val))


def _religion_group(religion: str) -> str:
    """Normalize a specific religion label to a broad group for conversion lookup."""
    r = religion.lower()
    if "islam" in r:         return "Islam"
    if "protestant" in r:    return "Protestant"
    if "catholic" in r:      return "Catholic"
    if "buddhist" in r or "taoist" in r: return "Buddhist"
    if "hindu" in r:         return "Hindu"
    if "jewish" in r or "judaism" in r:  return "Jewish"
    if "atheist" in r:       return "Atheist"
    if "agnostic" in r or "secular" in r or "none" in r: return "None/Agnostic"
    return "Other"


def _determine_conversion(
    religion_of_origin: str,
    age: int,
    has_intercultural_partner: bool,
) -> tuple[Optional[str], str, int]:
    """
    Probabilistically determine whether this agent converted religions.

    Returns:
        (converted_to_religion | None, conversion_type, conversion_age)
        conversion_type: "secular_drift" | "to_devout" | "interfaith_marriage_pressure" |
                         "genuine_conversion" | "none"
    """
    if age < 20:
        return None, "none", 0

    origin_group = _religion_group(religion_of_origin)

    # Intercultural partnership significantly raises conversion probability
    pressure_multiplier = 2.0 if has_intercultural_partner else 1.0

    # Collect all possible destination religions from this origin
    candidates: list[tuple[str, float]] = []
    for (frm, to_group), base_prob in CONVERSION_MAP.items():
        if frm == origin_group:
            adjusted = min(0.92, base_prob * pressure_multiplier)
            candidates.append((to_group, adjusted))

    # Roll each candidate independently
    for to_group, prob in candidates:
        if random.random() < prob:
            # Determine how the conversion happened
            if to_group in ("None/Agnostic", "Atheist"):
                conv_type = "secular_drift"
            elif has_intercultural_partner and random.random() < 0.60:
                conv_type = "interfaith_marriage_pressure"
            elif random.random() < 0.50:
                conv_type = "genuine_conversion"
            else:
                conv_type = "to_devout"

            # Age of conversion: must be after 18 and before current age
            conv_age = random.randint(18, max(19, age - 1))

            # Map group back to a readable religion label
            label_map = {
                "None/Agnostic": random.choice(["Agnostic", "None/No Religion"]),
                "Atheist":       "Atheist",
                "Protestant":    "Protestant",
                "Catholic":      "Catholic",
                "Islam":         "Islam",
                "Buddhist":      "Buddhism",
                "Jewish":        "Judaism",
                "Hindu":         "Hinduism",
                "Other":         "Spiritual/Other",
            }
            return label_map.get(to_group, to_group), conv_type, conv_age

    return None, "none", 0


# ─────────────────────────────────────────────────────────────────────────────
# PRIMARY PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────

def generate_cultural_profile(region: str, age: int) -> dict:
    """
    Generate a complete cultural and religious profile for one agent.

    Args:
        region: e.g. "Medan, Indonesia" or "North America"
        age:    agent's age in years

    Returns a dict with keys:
        ethnicity, cultural_primary, cultural_secondary,
        religion_of_origin, current_religion, religiosity,
        partner_culture, partner_religion,
        conversion_type, conversion_age,
        literacy, socioeconomic_friction,
        cultural_genome_modifiers   → {trait: int_delta} — apply to genome
        cultural_mutation_events    → [mutation_log entries] — prepend to Claude's log
        cultural_context_for_prompt → str — inject into Claude user prompt
    """
    ethnicity_pool = ETHNICITY_POOLS.get(region, ETHNICITY_POOLS["North America"])

    ethnicity = _weighted_choice(ethnicity_pool)
    cultural_primary = ethnicity

    # ── 1.b Determine if inherently bicultural ────────────────────────────────
    # Minorities surrounded by a dominant host culture are inherently bicultural.
    # We dynamically identify the dominant culture in this region as the one with 
    # the highest sampling weight.
    dominant_culture = max(ethnicity_pool, key=lambda x: x[1])[0]

    cultural_secondary: Optional[str] = None
    
    # If the chosen ethnicity is a minority in this region, they inherently adopt
    # the dominant culture as their secondary (host) culture.
    if ethnicity != dominant_culture:
        cultural_secondary = dominant_culture
    else:
        # If they ARE the dominant culture, ~12% chance of having a random secondary culture
        if random.random() < 0.12:
            alt_pool = [e for e, _ in ethnicity_pool if e != dominant_culture]
            if alt_pool:
                cultural_secondary = random.choice(alt_pool)

    # ── 2. Religion of origin ─────────────────────────────────────────────────
    religion_pool = RELIGION_BY_ETHNICITY.get(ethnicity, [("None/Agnostic", 1.0)])
    religion_of_origin = _weighted_choice(religion_pool)

    # ── 3. Base religiosity ───────────────────────────────────────────────────
    r_lo, r_hi = RELIGIOSITY_RANGES.get(religion_of_origin, (20, 70))
    religiosity = random.randint(r_lo, r_hi)

    # ── 4. Intercultural / interethnic partnership ─────────────────────────────
    ic_prob = INTERCULTURAL_MARRIAGE_PROB.get(region, 0.20)
    has_intercultural_partner = (age >= 22) and (random.random() < ic_prob)

    partner_culture: Optional[str] = None
    partner_religion: Optional[str] = None
    if has_intercultural_partner:
        diff_pool = [(e, w) for e, w in ethnicity_pool if e != ethnicity]
        if diff_pool:
            partner_culture = _weighted_choice(diff_pool)
            partner_rel_pool = RELIGION_BY_ETHNICITY.get(partner_culture, [("None/Agnostic", 1.0)])
            partner_religion = _weighted_choice(partner_rel_pool)

    # ── 5. Religious conversion ───────────────────────────────────────────────
    converted_to, conv_type, conv_age = _determine_conversion(
        religion_of_origin, age, has_intercultural_partner
    )
    current_religion = converted_to if converted_to else religion_of_origin

    # Adjust religiosity to be consistent with the conversion type
    if conv_type == "interfaith_marriage_pressure":
        new_lo, new_hi = RELIGIOSITY_RANGES.get(current_religion, (20, 70))
        # Reluctant converts tend to sit at the low-middle of the new faith's range
        religiosity = random.randint(new_lo, int(new_lo + (new_hi - new_lo) * 0.40))
    elif conv_type == "secular_drift":
        religiosity = random.randint(1, 20)
    elif conv_type in ("to_devout", "genuine_conversion"):
        new_lo, new_hi = RELIGIOSITY_RANGES.get(current_religion, (20, 70))
        religiosity = random.randint(int(new_lo + (new_hi - new_lo) * 0.50), new_hi)

    # ── 6. Socioeconomic friction & literacy (culturally grounded ranges) ──────
    sf_lo, sf_hi = SOCIOECONOMIC_FRICTION_RANGES.get(ethnicity, (20, 70))
    lit_lo, lit_hi = LITERACY_RANGES.get(ethnicity, (30, 75))

    # Intercultural marriage adds complexity → slight friction increase
    if has_intercultural_partner:
        sf_lo = min(sf_hi, sf_lo + 5)

    # Highly devout agents in conservative traditions can show suppressed literacy
    # (religious education over secular) — small effect
    if religiosity >= 75 and religion_of_origin in ("Islam (Devout)", "Islam", "Acehnese"):
        lit_hi = max(lit_lo + 5, lit_hi - 10)

    socioeconomic_friction = random.randint(sf_lo, sf_hi)
    literacy = random.randint(lit_lo, lit_hi)

    # ── 7. Accumulate genome modifiers ────────────────────────────────────────
    mods: dict[str, int] = {}

    def _add_mod(d: dict[str, int], scale: float = 1.0):
        for trait, delta in d.items():
            if trait == "family_orientation_proxy":  # Not a real genome column
                continue
            mods[trait] = mods.get(trait, 0) + int(delta * scale)

    _add_mod(CULTURE_MODIFIERS.get(ethnicity, {}))
    if cultural_secondary:
        _add_mod(CULTURE_MODIFIERS.get(cultural_secondary, {}), scale=0.45)

    if religiosity >= 60:
        _add_mod(RELIGIOSITY_MODIFIERS["devout"])
    elif religiosity <= 28:
        _add_mod(RELIGIOSITY_MODIFIERS["secular"])

    if has_intercultural_partner:
        _add_mod(INTERCULTURAL_MARRIAGE_MODIFIERS)

    if conv_type != "none":
        _add_mod(CONVERSION_MODIFIERS.get(conv_type, {}))

    # ── 8. Build mutation_log entries for cultural/religious events ────────────
    mutation_events: list[dict] = []

    # Cultural upbringing — always present
    cultural_mods = {k: v for k, v in CULTURE_MODIFIERS.get(ethnicity, {}).items()
                     if k != "family_orientation_proxy"}
    mutation_events.append({
        "life_stage": "Origin/Formation",
        "event_description": (
            f"Raised in a {ethnicity} household with {religion_of_origin} values. "
            f"Cultural norms — including family obligation structures, communication hierarchies, "
            f"and community expectations — shaped the foundational personality architecture."
        ),
        "trait_modifiers": cultural_mods,
    })

    # Bicultural upbringing
    if cultural_secondary:
        mutation_events.append({
            "life_stage": "Formation",
            "event_description": (
                f"Grew up navigating dual cultural identities ({ethnicity} and {cultural_secondary}). "
                f"Developed code-switching ability and a broader, more adaptive worldview — at the cost of "
                f"occasional identity ambiguity and belonging anxiety."
            ),
            "trait_modifiers": {"openness": 9, "neuroticism": 6, "communication_style": 5},
        })

    # Intercultural partnership
    if has_intercultural_partner:
        partner_desc = f"{partner_culture} background ({partner_religion})"
        mutation_events.append({
            "life_stage": "Independence",
            "event_description": (
                f"Entered an intercultural relationship/marriage with a partner of {partner_desc}. "
                f"Navigated family resistance, cultural negotiation, differing values on money, "
                f"child-rearing, and social obligations. Expanded worldview — but added identity tension."
            ),
            "trait_modifiers": INTERCULTURAL_MARRIAGE_MODIFIERS,
        })

    # Religious conversion
    if conv_type != "none" and converted_to:
        conv_stage = "Independence" if conv_age <= 35 else "Maturity"
        conv_descs = {
            "secular_drift": (
                f"Gradually drifted from {religion_of_origin} into a secular worldview through "
                f"university life, urban exposure, and intellectual community. "
                f"Institutional faith eroded slowly — replaced by personal ethics."
            ),
            "interfaith_marriage_pressure": (
                f"Formally converted from {religion_of_origin} to {converted_to} at age {conv_age} "
                f"to satisfy the conditions of marriage into partner's family. "
                f"The conversion is nominal — practiced outwardly, not deeply felt internally. "
                f"Carries quiet resentment and identity fragmentation."
            ),
            "genuine_conversion": (
                f"Authentically converted from {religion_of_origin} to {converted_to} at age {conv_age} "
                f"following a period of spiritual searching — triggered by personal crisis, community exposure, "
                f"or transformative relationship. The new faith became a genuine anchor."
            ),
            "to_devout": (
                f"Deepened from nominal {religion_of_origin} to full devotion to {converted_to} "
                f"at age {conv_age}. A revival experience, mentor relationship, or grief event "
                f"triggered the transformation. Religious identity now central to all decisions."
            ),
        }
        mutation_events.append({
            "life_stage": conv_stage,
            "event_description": conv_descs.get(conv_type, f"Converted from {religion_of_origin} to {converted_to}."),
            "trait_modifiers": CONVERSION_MODIFIERS.get(conv_type, {}),
        })

    # ── 9. Build Claude prompt context block ───────────────────────────────────
    religiosity_label = (
        "fundamentalist/devout" if religiosity >= 80 else
        "observant/practicing"  if religiosity >= 60 else
        "cultural but non-practicing" if religiosity >= 35 else
        "secular/post-religious"
    )

    lines = [
        "─── CULTURAL & RELIGIOUS PROFILE (MANDATORY CONSTRAINTS) ───",
        f"Ethnicity: {ethnicity}" + (f" | Also identifies with: {cultural_secondary}" if cultural_secondary else ""),
        f"Religion of origin: {religion_of_origin}",
        f"Current religion: {current_religion}" + (" ← CONVERTED" if converted_to else ""),
        f"Religiosity: {religiosity}/100 ({religiosity_label})",
    ]
    if has_intercultural_partner:
        lines.append(f"Partner: {partner_culture} | {partner_religion} (intercultural relationship — MUST appear in independence_layer)")
    if conv_type != "none" and converted_to:
        lines.append(f"Conversion: {religion_of_origin} → {converted_to} | Type: {conv_type.replace('_', ' ')} | Age: {conv_age}")
        lines.append("→ Conversion MUST appear explicitly in the appropriate life layer with realistic motivation and psychological aftermath.")
    lines += [
        f"",
        f"MANDATORY NARRATIVE RULES:",
        f"• All life layers must be internally consistent with this cultural/religious profile.",
        f"• {ethnicity} cultural norms (communication hierarchy, face-saving, filial obligation, status markers) must be present in origin_layer and formation_layer.",
        f"• The voice_print cultural_speech_markers must include {ethnicity}-authentic dialect, filler words, or code-switching phrases.",
        f"• Religious language in voice_print must reflect religiosity level {religiosity}/100.",
        f"• Do NOT re-add cultural/religious events to genome_mutation_log — they are handled separately.",
        "─────────────────────────────────────────────────────────────",
    ]
    cultural_context_for_prompt = "\n".join(lines)

    return {
        "ethnicity":                  ethnicity,
        "cultural_primary":           cultural_primary,
        "cultural_secondary":         cultural_secondary,
        "religion_of_origin":         religion_of_origin,
        "current_religion":           current_religion,
        "religiosity":                religiosity,
        "partner_culture":            partner_culture,
        "partner_religion":           partner_religion,
        "conversion_type":            conv_type,
        "conversion_age":             conv_age if conv_type != "none" else None,
        "literacy":                   literacy,
        "socioeconomic_friction":     socioeconomic_friction,
        "cultural_genome_modifiers":  mods,
        "cultural_mutation_events":   mutation_events,
        "cultural_context_for_prompt": cultural_context_for_prompt,
    }


def apply_cultural_modifiers(genome: dict, profile: dict) -> dict:
    """
    Apply the cultural/religious modifiers from a generated profile to a genome dict.
    Also directly sets literacy_and_articulation and socioeconomic_friction.
    All values are clamped to [1, 100].

    Args:
        genome:  dict of trait → int (e.g. from generate_random_genome())
        profile: dict returned by generate_cultural_profile()

    Returns:
        new genome dict with modifiers applied
    """
    g = genome.copy()
    for trait, delta in profile["cultural_genome_modifiers"].items():
        if trait in g:
            g[trait] = _clamp(g[trait] + delta)
    # Override these two with culturally-grounded values
    g["literacy_and_articulation"] = profile["literacy"]
    g["socioeconomic_friction"]    = profile["socioeconomic_friction"]
    return g
