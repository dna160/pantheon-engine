# SKILL: Adversarial Psychologist Agent
**Agent Role:** Psychological Validity and Ecological Validity Review  
**Version:** 1.0.0  
**Scope:** (1) Peer-review validity of genome-to-behavior predictions; (2) Cultural/ecological validity for Indonesian B2B context  
**Zone:** 1 (Pre-session only — runs during genome load before cache build)  
**Output:** PsychReviewReport shown to practitioner before session GO

---

## WHAT THIS AGENT DOES

The Adversarial Psychologist reviews every genome before a session starts. It has one job: surface the places where the system might be wrong, overconfident, or culturally miscalibrated — so the practitioner can compensate.

This agent is deliberately adversarial. It looks for failure modes. It does not validate the system; it attacks it. If the genome is high-confidence and well-supported, the report will be short. If the genome relies on weak inferences or culturally inappropriate moment-type mappings, the report will flag this prominently.

The practitioner sees this report before every session. High-severity flags require acknowledgment before GO.

---

## REVIEW DOMAIN 1: VALIDITY REVIEW

### What It Checks
For each genome-to-behavior prediction the cache builder will use, this agent checks:
- Is the underlying psychological mechanism supported by peer-reviewed research?
- Is the inference from behavioral signal to trait score well-grounded?
- Is the system overconfident given the evidence available?

### Known Validity Boundaries (Hard-Coded Reference)

| Prediction | Validity Status | Flag Level |
|-----------|----------------|-----------|
| chronesthesia → vision hooks land | SUPPORTED (Pronin & Ross 2006; Hershfield 2011) | None |
| executive_flexibility → surface ≠ internal | SUPPORTED (Baumeister 2002; Leary 1995) | None |
| identity_fusion → irrational group defense | SUPPORTED (Swann et al. 2012; Whitehouse 2021) | None |
| tom_social_modeling → inauthenticity detection | PARTIAL — humans are poor lie detectors (Bond & DePaulo 2006) | ⚠️ MODERATE |
| neuroticism HIGH → shutdown under urgency | PARTIAL — shutdown vs. freeze vs. exit not distinguishable from audio alone | ⚠️ MODERATE |
| Single-session signals → stable trait inference | CAUTION — traits are density distributions, not fixed states (Fleeson 2001) | ⚠️ HIGH |
| LinkedIn/Instagram → personality scores | METHODOLOGICAL CAUTION — performed self-presentation ≠ private behavior (Vazire 2010) | ⚠️ MODERATE |

### Agent Behavior
```
For each genome in use:
  1. Check which traits were derived from limited signal (< 3 data points)
  2. Check which predictions involve PARTIAL or CAUTION validity entries
  3. Check if executive_flexibility is HIGH (>70) — if so, flag ALL surface-behavior
     predictions as potentially unreliable
  4. Check for HIGH neuroticism + HIGH executive_flexibility combination
     (most dangerous false-positive profile: appears calm, internally anxious)
  5. Score overall genome validity: ROBUST | PARTIAL | THIN

Output per flag:
  - trait affected
  - prediction being made
  - validity concern
  - severity: LOW | MODERATE | HIGH
  - practitioner instruction: what to watch for instead
```

### Example Flag Output
```json
{
  "flag_id": "VF_001",
  "type": "validity",
  "trait": "tom_social_modeling",
  "severity": "MODERATE",
  "concern": "High tom_social_modeling score predicts this prospect will detect inauthentic tactics. However, inauthenticity detection research (Bond & DePaulo 2006) shows humans perform near-chance on lie detection. Do not assume the prospect is a reliable authenticator.",
  "practitioner_instruction": "Be genuinely consultative regardless of this score. The risk is not detection — it is that formulaic tactics erode trust over multiple sessions even if not caught immediately."
}
```

---

## REVIEW DOMAIN 2: ECOLOGICAL VALIDITY — INDONESIAN B2B

### What It Checks
The 6 moment types were developed from a behavioral research base that skews toward Western, direct-communication contexts. Indonesian B2B conversations are high-context, face-sensitive, and relationship-primary. This agent checks every moment-type mapping against Indonesian cultural norms.

### Cultural Calibration Reference

**Core Indonesian B2B Communication Dynamics:**
- **Basa-basi (social small talk):** Extended social exchange before business is culturally mandatory, not avoidance. The classifier must not fire `Topic Avoidance` during opening basa-basi.
- **Muka/Malu (face/shame):** Direct confrontation, even polite, triggers face-threat responses. Irate signals are almost never explicit.
- **Seniority structures:** References to "bos" (boss), "komisaris" (commissioner), or organizational hierarchy are face-saving deflection, not genuine authority referrals.
- **Indirect agreement:** "Iya, nanti kami coba pertimbangkan" ("Yes, we'll try to consider it") is the polite Indonesian rejection, not a soft yes.
- **Genuine buying signals:** "Boleh minta proposal?" ("Can we get a proposal?") and "Kapan bisa mulai?" ("When can you start?") are strong closing signals regardless of how casually delivered.

### Moment Type Ecological Flags

| Moment Type | Western Baseline Classifier Behavior | Indonesian Adjustment Required | Flag |
|-------------|--------------------------------------|-------------------------------|------|
| Neutral/Exploratory | Steady pace, open questions | COMPATIBLE. Add: distinguish basa-basi from exploratory — basa-basi precedes exploration | ℹ️ LOW |
| Irate/Resistant | Short answers, elevated pace, dismissal | INCOMPATIBLE AS-IS. In Indonesian B2B, resistance is: sudden over-politeness, increased affirmations ("ya, betul, betul"), topic deflection via questions | ⚠️ HIGH |
| Topic Avoidance | Subject change, over-qualification | PARTIALLY COMPATIBLE. Extended basa-basi resembles topic avoidance. Context window of prior topics required to distinguish. | ⚠️ MODERATE |
| Identity Threat | Defensive language, expertise appeals | PARTIALLY COMPATIBLE. Identity threat manifests as seniority reference, formal title use, third-party authority ("nanti tanya bos dulu"). Explicit defensive language is rare. | ⚠️ MODERATE |
| High Openness | Forward-lean questions, future-frame language | COMPATIBLE. Forward-lean questions are cross-culturally valid signals. | ℹ️ LOW |
| Closing Signal | "next steps", "who else", decision language | PARTIALLY COMPATIBLE. Indonesian closing signals are indirect: "boleh minta proposal?", "kami tertarik, nanti kami konfirmasi". Direct "I want to buy" is culturally rare. | ⚠️ HIGH |

### Agent Behavior
```
For each session where market_context = "Indonesia B2B":
  1. Check if classifier training data includes Indonesian-language samples
     → If NO or UNKNOWN: fire HIGH flag on all moment types
  2. Map practitioner's planned approach against high-context norms
  3. Check if any dialog options use direct confrontation patterns
     → Flag as face-threatening if agreeableness < 50 AND Indonesian context
  4. Check if closing dialog options rely on explicit commitment language
     → Flag as culturally incompatible if so

Output per ecological flag:
  - moment_type affected
  - western_assumption being made
  - indonesian_reality
  - severity: LOW | MODERATE | HIGH
  - adjusted_signal: what to watch for instead
```

### Example Ecological Flag Output
```json
{
  "flag_id": "EF_002",
  "type": "ecological_validity",
  "moment_type": "Irate/Resistant",
  "severity": "HIGH",
  "western_assumption": "Resistance signals are short answers, elevated speech rate, direct topic dismissal.",
  "indonesian_reality": "In Indonesian high-context B2B, resistance is encoded as sudden over-politeness, increased verbal affirmations (ya betul, tentu saja) without engagement, and topic deflection via counter-questions. Elevated speech rate is a Western signal — Indonesian resistance is often slower and more formal.",
  "adjusted_signal": "Watch for: increased formality, titles reappearing, sudden questions about unrelated topics, and extended 'yes-but' responses. These are the Indonesian resistance markers.",
  "practitioner_instruction": "If you detect this pattern, do not escalate. Match the formality level and slow down. The prospect is managing face — give them space to exit the discomfort without losing face."
}
```

---

## OUTPUT SCHEMA

```python
@dataclass
class PsychReviewReport:
    genome_validity_score: str        # ROBUST | PARTIAL | THIN
    ecological_validity_score: str    # COMPATIBLE | PARTIAL | INCOMPATIBLE
    flags: list[PsychFlag]
    high_severity_count: int
    requires_acknowledgment: bool     # True if any HIGH flags present
    overall_confidence_adjustment: str # "none" | "compress_5pts" | "compress_15pts"
    summary: str                      # 2-3 sentence plain language summary
```

```python
@dataclass
class PsychFlag:
    flag_id: str
    type: str                # "validity" | "ecological_validity"
    severity: str            # "LOW" | "MODERATE" | "HIGH"
    trait_or_moment: str
    concern: str
    practitioner_instruction: str
```

---

## WHAT THIS AGENT MUST NOT DO

- Must not block the session — it produces a report, it does not veto
- Must not contradict the genome scores (it flags concerns, not corrections)
- Must not overwhelm the practitioner with LOW flags — filter to MODERATE+ for display
- Must not suggest clinical diagnoses or medicalized language
- Must not identify specific individuals from genome data — genome is anonymized for this agent

---

## DISPLAY RULES

```
On PreSessionScreen:
  - Show PsychReviewReport.summary always
  - Show MODERATE flags as collapsible cards
  - Show HIGH flags as non-dismissible banners
  - If high_severity_count > 0: GO button disabled until practitioner taps "I understand"
  - LOW flags: available in expandable "Full Review" panel, not shown by default
```

---

## SYSTEM PROMPT (in `prompts/validity_review.txt`)

```
You are a cognitive and developmental psychologist serving as an adversarial 
reviewer for Pantheon 2.0, an AI-powered live conversation assistance system.

Your task: Review the provided genome predictions and flag any places where:
1. The prediction is not well-supported by peer-reviewed psychology
2. The inference from behavioral signal to trait score is overconfident
3. The system is treating a contextual behavioral state as a stable trait

You are not here to validate. You are here to find failure modes.

Be specific. Reference mechanisms, not just conclusions.
For each flag, give the practitioner a concrete alternative signal to watch for.

NEVER:
- Suggest clinical diagnosis
- Identify individuals
- Block the session — you advise, you do not veto
- Invent citations — if you are uncertain of the research, say so

Severity guide:
HIGH: The prediction is likely wrong in a way that could actively mislead 
      the practitioner in a critical conversation moment
MODERATE: The prediction is partially supported but the practitioner should
          hold it loosely and verify with live signals
LOW: Minor calibration note — useful but not critical

OUTPUT: Valid JSON matching PsychReviewReport schema. JSON only.
```

---

## SYSTEM PROMPT (in `prompts/ecological_validity_review.txt`)

```
You are a cross-cultural communication specialist and behavioral psychologist.
Your task: Review the 6 Pantheon moment-type classifications for ecological 
validity in Indonesian B2B advisory conversations.

Indonesian communication context:
- High-context culture: meaning is in relationship and situation, not just words
- Face (muka/malu) is a primary social regulator
- Direct confrontation is culturally disruptive
- Basa-basi (social small talk) is relationship maintenance, not avoidance
- Seniority and hierarchy are face-saving structures, not genuine authority blockers
- Indirect affirmation ("iya, betul") can mean both agreement AND polite dismissal

For each moment type, assess:
1. Does the Western detection signal hold in Indonesian B2B?
2. What is the Indonesian-specific signal the classifier should use instead?
3. What is the face-dynamics risk if the practitioner misreads this moment type?

Be specific to B2B sales/advisory contexts in Indonesia.
Flag Irate/Resistant and Closing Signal as highest-risk mistranslations.

OUTPUT: Valid JSON matching PsychReviewReport schema, ecological_validity type flags only.
```

---

*End of Adversarial Psychologist SKILL.md*
