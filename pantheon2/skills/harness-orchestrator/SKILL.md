# SKILL: Harness Orchestrator
**Agent Role:** Zone 1 and Zone 3 LLM Orchestration  
**Version:** 1.0.0  
**Scope:** Pre-session cache build + post-session genome analysis  
**Zone:** 1 (Pre-session) and 3 (Post-session) only. Never Zone 2.

---

## WHAT THIS AGENT DOES

The Harness Orchestrator is the LLM-facing layer of Pantheon 2.0. It runs exactly twice per session: once before the conversation begins (Zone 1) and once after it ends (Zone 3). During Zone 2 (live session), this agent is completely dormant.

Its two jobs are:
1. **Zone 1:** Given a prospect genome and RWI snapshot, produce a complete pre-computed dialog option tree (18 options across 6 moment types) calibrated to this specific human.
2. **Zone 3:** Given a session event log and outcome, analyze practitioner behavior patterns, surface genome mutation candidates, and update the practitioner self-profile.

---

## ZONE 1: CACHE BUILDER

### Input
```python
CacheBuilderInput:
  genome: dict              # 18-parameter genome, all INT 1–100
  confidence: str           # HIGH | MEDIUM | LOW
  rwi: RWISnapshot          # score (0–100), components
  psych_flags: list[str]    # adversarial review flags
  practitioner_profile: dict # practitioner's own genome parameters
  market_context: str       # "Indonesia B2B Advisory"
```

### Output
```python
DialogCache:
  moment_type_1:  # Neutral/Exploratory
    option_a: DialogOption{text, trigger_phrase_3_words, probability, rationale}
    option_b: DialogOption{...}
    option_c: DialogOption{...}
  moment_type_2:  # Irate/Resistant
    ...
  # ... × 6 moment types
```

---

## ZONE 3: SESSION ANALYZER

### Input
```python
SessionAnalyzerInput:
  session_log: list[SessionEvent]  # timestamped events
  outcome: str                     # "close_yes" | "close_no" | "follow_up"
  genome: dict                     # prospect genome at session start
  practitioner_profile: dict       # current practitioner genome
  option_choices: list[OptionChoice] # what practitioner chose vs. recommended
```

### Output
```python
SessionAnalysis:
  mutation_candidates: list[MutationCandidate]
  practitioner_deltas: list[PractitionerDelta]
  mirror_report: MirrorReport
  outcome_log: OutcomeEntry
```

---

## ADVERSARIAL CHECK: WHAT THIS AGENT MUST NOT DO

- Must not generate dialog options that exploit psychological vulnerabilities
- Must not recommend deception-adjacent tactics
- Must not surface a genome mutation candidate from a single observation
- Must not write to the genome directly — output candidates only

---

## PROVIDER SWITCHING

Edit `harness.config.json` only. Supported: `anthropic`, `openai`, `gemini`, `lmstudio`.

---

*End of Harness Orchestrator SKILL.md*
