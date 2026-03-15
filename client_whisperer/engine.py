import json
import os
from anthropic import Anthropic
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

load_dotenv("pantheon.env", override=True)

# ─────────────────────────────────────────────────────────────────────────────
# PROSPECT BLUEPRINT SYSTEM PROMPT
# Replaces GENESIS_SYSTEM_PROMPT for real prospect analysis.
# Unlike the synthetic agent seeder, this prompt treats LinkedIn/Instagram data
# as hard facts and forbids invented life events not supported by evidence.
# ─────────────────────────────────────────────────────────────────────────────
PROSPECT_BLUEPRINT_PROMPT = """You are a B2B psychographic analyst. You have been given scraped LinkedIn and Instagram data for a real professional, plus a genome inferred directly from that data.

Your job is to produce a structured life blueprint — NOT a creative fiction.

STRICT RULES:
1. Every life layer must be anchored to REAL data from the LinkedIn/Instagram inputs.
   - Education section → formation_layer
   - Career history (chronological) → independence_layer and maturity_layer
   - Recent activity, posts, bio, lifestyle signals → voice_print
2. DO NOT invent dramatic life events (divorces, bankruptcies, trauma, addiction) unless there is explicit evidence in the data.
3. Where data is missing, write "Insufficient data to determine." — do not fill gaps with plausible fiction.
4. The genome scores were inferred FROM this data — do not contradict them, but also do not fabricate new evidence to justify them.
5. genome_mutation_log: list only career transitions, role changes, or shifts visible in the actual data. 3–5 entries max.

OUTPUT FORMAT — respond with ONLY valid JSON, no markdown, no commentary:
{
  "origin_layer": {
    "summary": "string (what can be inferred about early background from education, location, name, cultural signals in the data)",
    "key_events": ["string — only data-supported inferences"],
    "psychological_impact": "string"
  },
  "formation_layer": {
    "summary": "string (education history from LinkedIn)",
    "key_events": ["string — actual schools, degrees, years from the data"],
    "psychological_impact": "string"
  },
  "independence_layer": {
    "summary": "string (early career from LinkedIn)",
    "key_events": ["string — actual roles and companies from career_trajectory"],
    "psychological_impact": "string"
  },
  "maturity_layer": {
    "summary": "string (current and recent senior career trajectory)",
    "key_events": ["string — actual roles and companies from career_trajectory"],
    "psychological_impact": "string"
  },
  "legacy_layer": {
    "summary": "string (trajectory inference — where are they headed based on current arc)",
    "key_events": ["string — only reasonable forward inferences, labelled as inferred"],
    "psychological_impact": "string"
  },
  "voice_print": {
    "vocabulary_level": "string (inferred from post quality, education, writing style)",
    "filler_words": ["string — from actual post language if available, else omit"],
    "cultural_speech_markers": ["string — from bio, posts, location signals"],
    "religious_language": ["string — only if explicitly visible in data, else empty array"],
    "persuasion_triggers": ["string — inferred from genome scores and data signals"],
    "conflict_style": "string"
  },
  "genome_mutation_log": [
    {
      "life_stage": "string (Formation|Independence|Maturity)",
      "event_description": "string — MUST be a real data point (e.g. 'Moved from X to Y role at Z company in YEAR')",
      "trait_modifiers": { "trait_name": integer_delta }
    }
  ]
}"""


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 1 — Genome Inference Model
# Derives the 18 integer trait scores from real scraped data signals.
# Mirrors the agent_genomes table schema exactly.
# ─────────────────────────────────────────────────────────────────────────────

class ProspectGenome(BaseModel):
    # Contextual inference (not stored in agent_genomes but needed for the prompt)
    inferred_age: int = Field(
        description="Estimated age from graduation year, career tenure, and experience durations."
    )
    inferred_region: str = Field(
        description=(
            "Geographic/cultural region. Use PANTHEON region labels where applicable: "
            "'Medan, Indonesia', 'North America', 'Singapore'. Otherwise use the most "
            "specific region available from their profile."
        )
    )
    inferred_background: str = Field(
        description=(
            "1-2 sentence cultural and demographic summary: ethnicity/nationality, "
            "professional class, religion signals (if any), and key identity markers "
            "visible from their profile and content."
        )
    )

    # ── Big Five + Behavioral Genome + Cognitive Architecture (mirrors agent_genomes columns)
    openness: int = Field(
        description=(
            "1-100. Rigidly traditional ↔ Radically curious. "
            "Evidence: career pivots, international roles, education breadth, "
            "unconventional interests or travel on Instagram, industry variety."
        )
    )
    conscientiousness: int = Field(
        description=(
            "1-100. Chaotically spontaneous ↔ Obsessively structured. "
            "Evidence: career progression consistency, LinkedIn completeness, "
            "posting regularity, titles held and tenure length, certifications."
        )
    )
    extraversion: int = Field(
        description=(
            "1-100. Deeply internal ↔ Compulsively social. "
            "Evidence: Instagram follower count relative to posting frequency, "
            "event/social/group content, network size, public speaking signals."
        )
    )
    agreeableness: int = Field(
        description=(
            "1-100. Confrontational ↔ Peace-seeking. "
            "Evidence: tone of LinkedIn posts and comments, collaborative vs competitive "
            "language, how they describe former employers, endorsement behavior."
        )
    )
    neuroticism: int = Field(
        description=(
            "1-100. Unshakably calm ↔ Chronically anxious. "
            "Evidence: sentiment volatility across posts, hustle culture references, "
            "career gap patterns, frequency of performance/achievement updates, "
            "vulnerability or stress signals in captions."
        )
    )
    communication_style: int = Field(
        description=(
            "1-100. Blunt/terse ↔ Diplomatic/verbose. "
            "Evidence: post and caption length, vocabulary range, hedging language, "
            "directness of LinkedIn posts, use of qualifiers."
        )
    )
    decision_making: int = Field(
        description=(
            "1-100. Gut instinct ↔ Analytical paralysis. "
            "Evidence: career move speed and boldness, industry consistency vs disruption, "
            "evidence of research-heavy behavior (thought leadership, data sharing), "
            "impulsive vs methodical progression pattern."
        )
    )
    brand_relationship: int = Field(
        description=(
            "1-100. Skeptical/anti-brand ↔ Brand-loyal evangelist. "
            "Evidence: Instagram brand tags and partnerships, luxury goods visibility, "
            "logo/brand clothing, product reviews, premium brand associations."
        )
    )
    influence_susceptibility: int = Field(
        description=(
            "1-100. Immune to social proof ↔ Heavily peer-influenced. "
            "Evidence: following count vs follower ratio, repost/share behavior, "
            "trend-following content, references to what peers are doing, "
            "crowd consensus language in posts."
        )
    )
    emotional_expression: int = Field(
        description=(
            "1-100. Stoic/reserved ↔ Explosive/transparent. "
            "Evidence: Instagram caption emotional depth, selfie frequency, personal story "
            "posts, vulnerability signals, emotional language in professional content."
        )
    )
    conflict_behavior: int = Field(
        description=(
            "1-100. Avoidant ↔ Confrontational. "
            "Evidence: LinkedIn comment directness, public disagreements, challenge posts, "
            "how directly they state opinions, industry controversy engagement."
        )
    )
    literacy_and_articulation: int = Field(
        description=(
            "1-100. Barely literate ↔ Eloquent/highly educated. "
            "Evidence: writing quality and complexity in posts, degree prestige and institution, "
            "vocabulary sophistication, use of technical language, publication history."
        )
    )
    socioeconomic_friction: int = Field(
        description=(
            "1-100. Comfortable/privileged trajectory ↔ Severe systemic barriers overcome. "
            "Evidence: name-brand schools and companies, international career geography, "
            "visible financial signals (travel, lifestyle), scholarship vs fee-paying signals, "
            "upward mobility pace vs expected trajectory for their background."
        )
    )

    # ── Cognitive Architecture Traits ─────────────────────────────────────────
    identity_fusion: int = Field(
        description=(
            "1-100. Low=individualist, High=group-fused. "
            "Evidence: LinkedIn mentions of team/community, Instagram group content, "
            "clan/family references, collective language patterns."
        )
    )
    chronesthesia_capacity: int = Field(
        description=(
            "1-100. Low=present-focused, High=vivid future planner. "
            "Evidence: strategic career moves, vision-oriented posts, "
            "long-term planning language."
        )
    )
    tom_self_awareness: int = Field(
        description=(
            "1-100. Evidence: self-deprecating humor, introspective posts, "
            "acknowledgment of own biases, vulnerability signals."
        )
    )
    tom_social_modeling: int = Field(
        description=(
            "1-100. Evidence: diplomatic language, audience-calibrated messaging, "
            "sophisticated relationship management signals."
        )
    )
    executive_flexibility: int = Field(
        description=(
            "1-100. Evidence: professional composure vs emotional leakage, "
            "controlled persona vs raw expression, context-switching ability."
        )
    )


# ─────────────────────────────────────────────────────────────────────────────
# INTERNAL HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _format_posts_block(posts_data: Dict[str, Any]) -> str:
    """
    Formats LinkedIn posts with recency tiers for injection into prompts.
    HOT  = recency_weight >= 0.70  (< ~30 days)
    WARM = recency_weight >= 0.35  (30–90 days)
    COLD = recency_weight <  0.35  (> 90 days)
    """
    posts = posts_data.get("posts", [])
    if not posts:
        return "No LinkedIn post data available."

    lines = [f"LinkedIn Posts ({len(posts)} fetched, sorted newest-first):"]
    for p in posts:
        weight = p.get("recency_weight", 0)
        days   = p.get("days_ago")
        tier   = "HOT" if weight >= 0.70 else ("WARM" if weight >= 0.35 else "COLD")
        age    = f"{days}d ago" if days is not None else "date unknown"
        eng    = f"👍{p.get('likes', 0)} 💬{p.get('comments', 0)} 🔁{p.get('shares', 0)}"
        ptype  = p.get("post_type", "post").upper()
        text   = p.get("text", "").strip()[:400]  # cap length per post
        lines.append(
            f"\n  [{tier} | {age} | weight:{weight} | {ptype} | {eng}]\n  \"{text}\""
        )

    return "\n".join(lines)


def _infer_genome(
    linkedin_data: Dict[str, Any],
    posts_data: Dict[str, Any],
    insta_data: Dict[str, Any],
    vision_insights: Dict[str, Any],
    client: Anthropic
) -> dict:
    """
    Phase 1: Derive the 18-trait personality genome from scraped social signals.
    Vision insights are primary evidence — they calibrate genome scores directly,
    not merely as supplemental context.
    """
    tool_schema = {
        "name": "infer_genome",
        "description": "Infer the personality genome and contextual profile from scraped social data.",
        "input_schema": ProspectGenome.model_json_schema()
    }

    system = (
        "You are a behavioral analyst and B2B psychographic profiler. "
        "Given scraped LinkedIn, Instagram, and direct image analysis of a real prospect, "
        "infer their personality genome — 18 integer scores (1-100) that represent who they are.\n\n"
        "SCORING RULES:\n"
        "- Every score must be anchored to specific evidence. Cite it mentally before scoring.\n"
        "- Do NOT default to middle-range scores (40-60) unless evidence is genuinely ambiguous.\n"
        "- Push toward confident, evidence-grounded extremes.\n"
        "- Vision data carries the same evidentiary weight as LinkedIn data. "
        "Treat image-derived signals as OBSERVED FACTS, not inferences to be discounted.\n\n"
        "VISION → GENOME CALIBRATION RULES:\n"
        "  brand_signals visible (luxury, premium brands) → brand_relationship += 15-25\n"
        "  lifestyle_choices include 'fitness-focused' or 'wellness-driven' → conscientiousness += 10\n"
        "  lifestyle_choices include 'luxury consumer' or 'status-oriented' → "
        "socioeconomic_friction -= 10 (lower barrier = more privileged)\n"
        "  social_environment = 'mostly solo' or 'private' → extraversion -= 15\n"
        "  social_environment = 'large social network' or 'frequent group events' → extraversion += 15\n"
        "  self_presentation_style = 'curated/polished' → conscientiousness += 10, "
        "emotional_expression -= 10 (controls outward emotion)\n"
        "  self_presentation_style = 'candid/unfiltered' → openness += 10, emotional_expression += 10\n"
        "  self_presentation_style = 'aspirational/status-oriented' → "
        "influence_susceptibility += 10, brand_relationship += 10\n"
        "  body_language_and_confidence = 'high confidence' or 'direct camera engagement' → "
        "extraversion += 10, conflict_behavior += 5\n"
        "  body_language_and_confidence = 'private/avoidant of camera' → "
        "extraversion -= 10, emotional_expression -= 10\n"
        "  apparent_life_stage = 'young professional' → openness += 5, neuroticism += 5\n"
        "  apparent_life_stage = 'established executive with family' → "
        "conscientiousness += 10, agreeableness += 5, neuroticism -= 10\n"
        "  privacy_flags present → emotional_expression -= 10, influence_susceptibility -= 10\n"
        "  current_emotional_sentiment positive/energetic → neuroticism -= 10\n"
        "  current_emotional_sentiment stressed/anxious → neuroticism += 15\n"
        "  Hobbies showing intellectual depth (arts, reading, research) → openness += 10\n"
        "  Hobbies showing social breadth (events, sports, travel) → extraversion += 10\n"
        "Apply these adjustments BEFORE finalising scores, not as post-hoc justification."
    )

    posts_block = _format_posts_block(posts_data)

    # Build structured vision calibration block for the prompt
    vi = vision_insights or {}
    vision_calibration_block = (
        f"VISION ANALYSIS — TREAT AS OBSERVED FACTS (same weight as LinkedIn):\n"
        f"  Hobbies observed in images:   {', '.join(vi.get('hobbies', [])) or 'None detected'}\n"
        f"  Lifestyle choices:            {', '.join(vi.get('lifestyle_choices', [])) or 'None detected'}\n"
        f"  Relationship / family status: {vi.get('relationship_status', 'Unknown')}\n"
        f"  Current emotional sentiment:  {vi.get('current_emotional_sentiment', 'Unknown')}\n"
        f"  Social environment:           {vi.get('social_environment', 'Unknown')}\n"
        f"  Brand signals visible:        {', '.join(vi.get('brand_signals', [])) or 'None detected'}\n"
        f"  Self-presentation style:      {vi.get('self_presentation_style', 'Unknown')}\n"
        f"  Body language / confidence:   {vi.get('body_language_and_confidence', 'Unknown')}\n"
        f"  Apparent life stage (visual): {vi.get('apparent_life_stage', 'Unknown')}\n"
        f"  Privacy flags:                {'; '.join(vi.get('privacy_flags', [])) or 'None'}\n"
        f"  Images analysed:              {vi.get('image_count_analysed', 0)}\n\n"
        f"CALIBRATION INSTRUCTION: Apply the vision→genome calibration rules from the system prompt "
        f"to adjust scores based on the above vision evidence BEFORE considering LinkedIn data. "
        f"Then reconcile with LinkedIn evidence. Where vision and LinkedIn conflict, "
        f"use whichever is more recent and specific."
    )

    response = client.messages.create(
        model="claude-sonnet-4-6",
        system=system,
        max_tokens=2000,
        tools=[tool_schema],
        tool_choice={"type": "tool", "name": "infer_genome"},
        messages=[{
            "role": "user",
            "content": (
                "Infer the personality genome for this prospect.\n\n"
                f"{vision_calibration_block}\n"
                f"--- LinkedIn Profile ---\n{json.dumps(linkedin_data, indent=2, default=str)}\n\n"
                f"--- LinkedIn Posts (recency-weighted — HOT = current mindset) ---\n"
                f"{posts_block}\n\n"
                "NOTE ON POSTS: HOT posts reflect current priorities, vocabulary, and emotional register. "
                "Use them to calibrate: communication_style, emotional_expression, conflict_behavior, "
                "openness, neuroticism, literacy_and_articulation.\n\n"
                f"--- Instagram Metadata ---\n{json.dumps(insta_data, indent=2, default=str)}"
            )
        }]
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "infer_genome":
            return block.input

    raise RuntimeError("Genome inference did not return structured output.")


def _build_genesis_prompt(genome: dict, linkedin_data: dict, posts_data: dict, insta_data: dict, vision_insights: dict) -> str:
    """
    Build the user prompt for PROSPECT_BLUEPRINT_PROMPT.
    Vision insights are injected as hard facts with explicit life-layer
    population instructions — same evidentiary weight as LinkedIn.
    """
    g = genome
    vi = vision_insights or {}

    # Build a structured vision evidence block that directly maps to life layers
    hobbies        = ', '.join(vi.get('hobbies', [])) or 'None confirmed'
    lifestyle      = ', '.join(vi.get('lifestyle_choices', [])) or 'None confirmed'
    relationship   = vi.get('relationship_status', 'Unknown')
    sentiment      = vi.get('current_emotional_sentiment', 'Unknown')
    social_env     = vi.get('social_environment', 'Unknown')
    brands         = ', '.join(vi.get('brand_signals', [])) or 'None detected'
    self_pres      = vi.get('self_presentation_style', 'Unknown')
    body_lang      = vi.get('body_language_and_confidence', 'Unknown')
    life_stage_vis = vi.get('apparent_life_stage', 'Unknown')
    privacy_flags  = '; '.join(vi.get('privacy_flags', [])) or 'None'
    img_count      = vi.get('image_count_analysed', 0)
    actionable     = vi.get('actionable_insights', [])

    vision_evidence_block = (
        f"═══ VISION EVIDENCE ({img_count} images analysed — treat as observed facts) ═══\n"
        f"WHAT THE IMAGES SHOW:\n"
        f"  Activities / hobbies visible: {hobbies}\n"
        f"  Lifestyle signals:            {lifestyle}\n"
        f"  Relationship / family status: {relationship}\n"
        f"  Brand signals visible:        {brands}\n"
        f"  Emotional tone of posts:      {sentiment}\n"
        f"  Social environment:           {social_env}\n"
        f"  Self-presentation strategy:   {self_pres}\n"
        f"  Physical confidence / presence: {body_lang}\n"
        f"  Visual life stage:            {life_stage_vis}\n"
        f"  Privacy sensitivity flags:    {privacy_flags}\n"
        + (
            f"\nIMAGE-DERIVED CONVERSATION SIGNALS:\n" +
            "\n".join(f"  • {a}" for a in actionable)
            if actionable else ""
        ) +
        f"\n\nLIFE LAYER POPULATION INSTRUCTIONS — use vision evidence to build each layer:\n"
        f"  INDEPENDENCE LAYER (18-35 yrs): Use hobbies, lifestyle_choices, and social_environment "
        f"to describe activities, friend groups, and identity-forming experiences in this period. "
        f"If '{hobbies}' includes travel, fitness, or culture — these belong here as key_events.\n"
        f"  MATURITY LAYER (35-60 yrs): Use relationship_status='{relationship}' and "
        f"apparent_life_stage='{life_stage_vis}' to determine family formation, career consolidation, "
        f"and wealth accumulation events. Brand signals ('{brands}') indicate financial positioning.\n"
        f"  VOICE PRINT: Use self_presentation_style='{self_pres}' and body_language='{body_lang}' "
        f"to calibrate communication register and authenticity level. Curated = controlled emotional "
        f"expression. Candid = comfortable with vulnerability. "
        f"Use emotional_sentiment='{sentiment}' to set current persuasion triggers.\n"
        f"  GENOME MUTATION LOG: Every confirmed lifestyle image signal should generate a mutation "
        f"entry. Example: confirmed fitness lifestyle → mutation 'Adopted discipline-first lifestyle "
        f"→ raised conscientiousness'. Brand signals → mutation 'Consolidated status identity "
        f"→ raised brand_relationship'. These are real mutations anchored to visual evidence.\n"
        f"RULE: Do NOT invent life events not evidenced by either LinkedIn or vision data. "
        f"But DO fully use the vision evidence to populate layers — it is real data."
    )

    return (
        f"Build a structured psychographic profile for this real prospect.\n\n"
        f"INFERRED CONTEXT (derived from the data below):\n"
        f"  Age: ~{g['inferred_age']} | Region: {g['inferred_region']}\n"
        f"  Background: {g['inferred_background']}\n\n"
        f"GENOME SCORES (already calibrated against vision + LinkedIn — use to verify layer consistency):\n"
        f"  openness={g['openness']}, conscientiousness={g['conscientiousness']}, "
        f"extraversion={g['extraversion']}, agreeableness={g['agreeableness']}, "
        f"neuroticism={g['neuroticism']}, communication_style={g['communication_style']}, "
        f"decision_making={g['decision_making']}, brand_relationship={g['brand_relationship']}, "
        f"influence_susceptibility={g['influence_susceptibility']}, "
        f"emotional_expression={g['emotional_expression']}, "
        f"conflict_behavior={g['conflict_behavior']}, "
        f"literacy_and_articulation={g['literacy_and_articulation']}, "
        f"socioeconomic_friction={g['socioeconomic_friction']}, "
        f"identity_fusion={g['identity_fusion']}, "
        f"chronesthesia_capacity={g['chronesthesia_capacity']}, "
        f"tom_self_awareness={g['tom_self_awareness']}, "
        f"tom_social_modeling={g['tom_social_modeling']}, "
        f"executive_flexibility={g['executive_flexibility']}\n\n"
        f"{vision_evidence_block}\n\n"
        f"═══ LINKEDIN EVIDENCE ═══\n"
        f"--- LinkedIn Profile ---\n{json.dumps(linkedin_data, indent=2, default=str)}\n\n"
        f"--- LinkedIn Posts (recency-weighted) ---\n{_format_posts_block(posts_data)}\n\n"
        "POSTS INSTRUCTION: HOT posts reflect who this person is RIGHT NOW. "
        "Use their vocabulary, topics, and emotional tone directly in voice_print.\n\n"
        f"--- Instagram Metadata ---\n{json.dumps(insta_data, indent=2, default=str)}\n\n"
        f"Output ONLY valid JSON. Every life layer must reference at least one specific data point "
        f"from either LinkedIn or vision evidence — no invented events."
    )


def _format_for_strategy(genome: dict, blueprint: dict, posts_data: dict, vision_insights: dict = None) -> str:
    """
    Formats the genome + PANTHEON life blueprint into a rich structured string
    for human_whisperer.py. Includes genome scores, all life layers, voice print,
    mutation log, live post signals, and vision-derived actionable insights.
    """
    def layer_text(title: str, data: dict) -> str:
        if not data:
            return ""
        events = "\n".join(f"    - {e}" for e in data.get("key_events", []))
        return (
            f"  [{title}]\n"
            f"  {data.get('summary', '')}\n"
            f"  Key events:\n{events}\n"
            f"  Psychological impact: {data.get('psychological_impact', '')}\n"
        )

    vp = blueprint.get("voice_print", {})
    voice_section = (
        f"  Vocabulary: {vp.get('vocabulary_level', 'N/A')}\n"
        f"  Filler words: {', '.join(vp.get('filler_words', []))}\n"
        f"  Persuasion triggers: {', '.join(vp.get('persuasion_triggers', []))}\n"
        f"  Conflict style: {vp.get('conflict_style', 'N/A')}\n"
        f"  Speech markers: {', '.join(vp.get('cultural_speech_markers', []))}\n"
    )

    mutations = "\n".join(
        f"  [{m.get('life_stage', '')}] {m.get('event_description', '')}"
        for m in blueprint.get("genome_mutation_log", [])
    )

    # ── Recent LinkedIn Posts Signal ──────────────────────────────────────────
    hot_posts  = [p for p in posts_data.get("posts", []) if p.get("recency_weight", 0) >= 0.70]
    warm_posts = [p for p in posts_data.get("posts", []) if 0.35 <= p.get("recency_weight", 0) < 0.70]

    def post_line(p: dict) -> str:
        days  = p.get("days_ago")
        age   = f"{days}d ago" if days is not None else "?"
        eng   = f"👍{p.get('likes',0)} 💬{p.get('comments',0)} 🔁{p.get('shares',0)}"
        text  = p.get("text", "").strip()[:300]
        return f'    [{age} | {eng}] "{text}"'

    posts_section_lines = ["── LIVE POST SIGNALS (use for warm-up openers) ──"]
    if hot_posts:
        posts_section_lines.append("  [HOT — current mindset]")
        posts_section_lines.extend(post_line(p) for p in hot_posts[:3])
    if warm_posts:
        posts_section_lines.append("  [WARM — recent themes]")
        posts_section_lines.extend(post_line(p) for p in warm_posts[:3])
    if not hot_posts and not warm_posts:
        posts_section_lines.append("  No recent posts available.")
    posts_section = "\n".join(posts_section_lines)

    # ── Vision Insights ───────────────────────────────────────────────────────
    vi = vision_insights or {}
    vision_lines = ["── VISION INSIGHTS (from actual image analysis) ──"]

    actionable = vi.get("actionable_insights", [])
    if actionable:
        vision_lines.append("  [ACTIONABLE CONVERSATION LEVERS]")
        for insight in actionable:
            vision_lines.append(f"    • {insight}")
    else:
        vision_lines.append("  No vision-derived conversation levers available.")

    sentiment      = vi.get("current_emotional_sentiment", "")
    social_env     = vi.get("social_environment", "")
    self_pres      = vi.get("self_presentation_style", "")
    body_lang      = vi.get("body_language_and_confidence", "")
    life_stage_vis = vi.get("apparent_life_stage", "")
    brands         = ", ".join(vi.get("brand_signals", [])) or "None detected"
    privacy_flags  = vi.get("privacy_flags", [])
    img_count      = vi.get("image_count_analysed", 0)

    vision_lines.extend([
        f"  Images analysed: {img_count}",
        f"  Emotional sentiment: {sentiment}",
        f"  Social environment: {social_env}",
        f"  Self-presentation: {self_pres}",
        f"  Body language / confidence: {body_lang}",
        f"  Apparent life stage (visual): {life_stage_vis}",
        f"  Brand signals: {brands}",
    ])
    if privacy_flags:
        vision_lines.append("  [PRIVACY FLAGS — approach with care]")
        for flag in privacy_flags:
            vision_lines.append(f"    ⚠ {flag}")

    vision_section = "\n".join(vision_lines)

    g = genome
    return "\n".join([
        "═══ PANTHEON LIFE BLUEPRINT ═══",
        f"Age: {g['inferred_age']} | Region: {g['inferred_region']}",
        f"Background: {g['inferred_background']}",
        "",
        "── PERSONALITY GENOME (1-100) ──",
        f"  Openness {g['openness']} | Conscientiousness {g['conscientiousness']} | "
        f"Extraversion {g['extraversion']} | Agreeableness {g['agreeableness']} | "
        f"Neuroticism {g['neuroticism']}",
        f"  Communication style {g['communication_style']} (1=blunt, 100=diplomatic) | "
        f"Decision-making {g['decision_making']} (1=gut, 100=analytical)",
        f"  Brand relationship {g['brand_relationship']} | "
        f"Influence susceptibility {g['influence_susceptibility']}",
        f"  Emotional expression {g['emotional_expression']} | "
        f"Conflict behavior {g['conflict_behavior']} (1=avoidant, 100=confrontational)",
        f"  Literacy & articulation {g['literacy_and_articulation']} | "
        f"Socioeconomic friction {g['socioeconomic_friction']} (1=privileged, 100=barriers)",
        f"  Identity fusion {g['identity_fusion']} (1=individualist, 100=group-fused) | "
        f"Chronesthesia capacity {g['chronesthesia_capacity']} (1=present-only, 100=future-planner)",
        f"  ToM self-awareness {g['tom_self_awareness']} (1=blind to own states, 100=deep self-reflection) | "
        f"ToM social modeling {g['tom_social_modeling']} (1=oblivious to others, 100=reads rooms perfectly)",
        f"  Executive flexibility {g['executive_flexibility']} (1=traits leak always, 100=can override impulses)",
        "",
        "── LIFE LAYERS ──",
        layer_text("ORIGIN LAYER  0-5 yrs",   blueprint.get("origin_layer", {})),
        layer_text("FORMATION LAYER  5-18 yrs", blueprint.get("formation_layer", {})),
        layer_text("INDEPENDENCE LAYER  18-35 yrs", blueprint.get("independence_layer", {})),
        layer_text("MATURITY LAYER  35-60 yrs", blueprint.get("maturity_layer", {})),
        "",
        "── VOICE PRINT ──",
        voice_section,
        "── KEY LIFE MUTATIONS ──",
        mutations,
        "",
        posts_section,
        "",
        vision_section,
        "═══════════════════════════════",
    ])


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────

def _save_to_supabase(
    prospect_name: str,
    genome: dict,
    blueprint: dict,
) -> str | None:
    """
    Persist the prospect's genome + life blueprint to the agent_genomes table.
    Returns the inserted row's UUID, or None if the save fails.
    """
    try:
        from supabase import create_client
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            print("  [Pantheon] Supabase credentials missing — skipping DB save.")
            return None

        sb = create_client(url, key)

        row = {
            "target_demographic": f"Prospect: {prospect_name}",
            "age":                genome.get("inferred_age"),
            "region":             genome.get("inferred_region"),
            # 18-trait genome
            "openness":               genome.get("openness"),
            "conscientiousness":      genome.get("conscientiousness"),
            "extraversion":           genome.get("extraversion"),
            "agreeableness":          genome.get("agreeableness"),
            "neuroticism":            genome.get("neuroticism"),
            "communication_style":    genome.get("communication_style"),
            "decision_making":        genome.get("decision_making"),
            "brand_relationship":     genome.get("brand_relationship"),
            "influence_susceptibility": genome.get("influence_susceptibility"),
            "emotional_expression":   genome.get("emotional_expression"),
            "conflict_behavior":      genome.get("conflict_behavior"),
            "literacy_and_articulation": genome.get("literacy_and_articulation"),
            "socioeconomic_friction": genome.get("socioeconomic_friction"),
            # Cognitive architecture traits
            "identity_fusion":        genome.get("identity_fusion"),
            "chronesthesia_capacity": genome.get("chronesthesia_capacity"),
            "tom_self_awareness":     genome.get("tom_self_awareness"),
            "tom_social_modeling":    genome.get("tom_social_modeling"),
            "executive_flexibility":  genome.get("executive_flexibility"),
            # Life blueprint layers
            "origin_layer":       blueprint.get("origin_layer"),
            "formation_layer":    blueprint.get("formation_layer"),
            "independence_layer": blueprint.get("independence_layer"),
            "maturity_layer":     blueprint.get("maturity_layer"),
            "legacy_layer":       blueprint.get("legacy_layer"),
            "voice_print":        blueprint.get("voice_print"),
            "genome_mutation_log": blueprint.get("genome_mutation_log"),
        }

        response = sb.table("agent_genomes").insert(row).execute()
        genome_id = response.data[0]["id"] if response.data else None
        print(f"  [Pantheon] Genome saved to DB — id: {genome_id}")
        return genome_id

    except Exception as e:
        print(f"  [Pantheon] DB save failed (non-fatal): {e}")
        return None


def run_pantheon_simulation(
    linkedin_data: Dict[str, Any],
    insta_data: Dict[str, Any],
    vision_insights: Dict[str, Any],
    posts_data: Optional[Dict[str, Any]] = None,
) -> dict:
    """
    Two-phase Pantheon simulation for a real B2B prospect.

    Phase 1 — Genome inference:
      Derives the 18-trait personality genome (same schema as agent_genomes table)
      from scraped LinkedIn, Instagram, and vision data.
      Every score is anchored to specific evidence — not randomised.

    Phase 2 — Life blueprint generation:
      Uses the authoritative GENESIS_SYSTEM_PROMPT (shared with all synthetic
      agent seeding) to produce the full JSONB life blueprint:
        - origin_layer, formation_layer, independence_layer, maturity_layer, legacy_layer
        - voice_print (vocabulary, filler words, persuasion triggers, conflict style)
        - genome_mutation_log (life events that explain the final genome scores)

    Returns:
        {
            "simulated_life": str,   # formatted blueprint for strategy.py
            "genome_id":      str | None,  # UUID of the saved agent_genomes row
            "prospect_name":  str,   # extracted from linkedin_data
        }
    """
    client = Anthropic()
    if posts_data is None:
        posts_data = {}

    # ── Phase 1: Infer genome from real data ──────────────────────────────────
    print("  [Pantheon] Phase 1: Inferring personality genome from scraped signals...")
    genome = _infer_genome(linkedin_data, posts_data, insta_data, vision_insights, client)
    print(
        f"  [Pantheon] Genome inferred — age:{genome['inferred_age']} | "
        f"region:{genome['inferred_region']} | "
        f"O:{genome['openness']} C:{genome['conscientiousness']} "
        f"E:{genome['extraversion']} A:{genome['agreeableness']} N:{genome['neuroticism']}"
    )

    # ── Phase 2: Full life blueprint via GENESIS_SYSTEM_PROMPT ───────────────
    print("  [Pantheon] Phase 2: Building life blueprint via Genesis engine...")
    user_prompt = _build_genesis_prompt(genome, linkedin_data, posts_data, insta_data, vision_insights)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        system=PROSPECT_BLUEPRINT_PROMPT,
        max_tokens=4000,
        messages=[{"role": "user", "content": user_prompt}]
    )

    raw = response.content[0].text.strip()
    # Strip accidental markdown fences (same guard as seed.py)
    if raw.startswith("```json"): raw = raw[7:]
    if raw.startswith("```"):     raw = raw[3:]
    if raw.endswith("```"):       raw = raw[:-3]
    raw = raw.strip()

    blueprint = json.loads(raw)
    print("  [Pantheon] Blueprint generated successfully.")

    # ── Persist to Supabase ───────────────────────────────────────────────────
    prospect_name = linkedin_data.get("name", "Unknown Prospect")
    genome_id = _save_to_supabase(prospect_name, genome, blueprint)

    return {
        "simulated_life": _format_for_strategy(genome, blueprint, posts_data, vision_insights),
        "genome_id":      genome_id,
        "prospect_name":  prospect_name,
    }
