from anthropic import Anthropic
from pydantic import BaseModel, Field
from typing import List, Annotated
from client_whisperer.human_whisperer import EngagementHookCard


class PredictabilityScores(BaseModel):
    initial_score: int = Field(
        description=(
            "Chances of closing this prospect based purely on raw profile fit with the product (0-100). "
            "Weight these genome signals directly:\n"
            "  + Conscientiousness (high) → reliable buyer, follows through on decisions\n"
            "  + Openness (high) → receptive to new solutions and category creation\n"
            "  + Brand_relationship (high) → responds to premium brand positioning\n"
            "  - Neuroticism (high) → risk-averse, needs safety signals, slows decisions\n"
            "  - Socioeconomic_friction (high) → budget is a genuine constraint\n"
            "  - Decision_making (high = analytical) → long sales cycle, demands evidence\n"
            "Also weigh: seniority and budget authority from their career data, "
            "industry alignment with the product's target market, and whether they "
            "visibly have the problem the product solves."
        )
    )
    post_approach_score: int = Field(
        description=(
            "Chances of closing this prospect if the warm-up strategy and probing questions "
            "are executed correctly (0-100). Must always exceed initial_score — the gap IS the strategy's value.\n"
            "Additional genome signals that the approach can activate:\n"
            "  + Influence_susceptibility (high) → social proof and peer success stories will land\n"
            "  + Emotional_expression (high) → personal connection and empathy will accelerate trust\n"
            "  + Agreeableness (high) → once rapport is built, friction drops significantly\n"
            "  + Decision_making (low = gut instinct) → vision and story close faster than data\n"
            "  - Conflict_behavior (high) → will push back hard; needs strong reframe\n"
            "  - Influence_susceptibility (low) → immune to social proof; needs internal conviction"
        )
    )


class TrajectoryTimeline(BaseModel):
    month_3: str = Field(
        description=(
            "Conversion likelihood at 3 months. Reference specific signals: "
            "current role tenure and whether they're in a decision-making window, "
            "any visible urgency signals (job change, company growth, funding), "
            "and their decision_making genome score (low=fast mover, high=slow deliberator). "
            "Format: likelihood label (High/Medium/Low) + 1-sentence reasoning from their profile."
        )
    )
    month_6: str = Field(
        description=(
            "Conversion likelihood at 6 months. Consider: budget cycle alignment, "
            "career progression pace (are they likely to get promoted or change roles?), "
            "and whether the product's value increases or decreases as their trajectory continues. "
            "Format: likelihood label + 1-sentence reasoning."
        )
    )
    year_1: str = Field(
        description=(
            "Conversion likelihood at 1 year. Factor in likely role changes or promotions "
            "based on their career arc velocity. Will they have more authority and budget, "
            "or will they have moved on? Reference their conscientiousness and decision_making scores. "
            "Format: likelihood label + 1-sentence reasoning."
        )
    )
    year_2: str = Field(
        description=(
            "Conversion likelihood at 2 years. Long-range view based on life trajectory — "
            "are they on a path that increases or decreases alignment with this product's "
            "value proposition? Reference their openness and career pattern. "
            "Format: likelihood label + 1-sentence reasoning."
        )
    )


class ClientWhispererStrategy(BaseModel):
    engagement_hook_card: EngagementHookCard
    warm_up_strategy: Annotated[List[str], Field(min_length=3, max_length=3)] = Field(
        description=(
            "Exactly 3 specific, ready-to-use conversation openers. Each must:\n"
            "  1. Be drawn directly from a real signal in the life blueprint "
            "(career milestone, lifestyle signal, life event, mutual reference point)\n"
            "  2. Be calibrated to their communication_style genome score "
            "(low score = be direct and brief; high score = be warm and expansive)\n"
            "  3. Make them feel seen without feeling surveilled\n"
            "  4. Be a complete, actionable opener — not a topic label.\n"
            "Bad: 'Their love of travel'\n"
            "Good: 'You've been posting from Bali twice this year — "
            "are you building toward a remote setup, or just decompressing?'"
        )
    )
    probing_questions: Annotated[List[str], Field(min_length=3, max_length=3)] = Field(
        description=(
            "Exactly 3 high-leverage questions that expose this prospect's specific pain points. "
            "Each question must:\n"
            "  1. Be anchored to a real signal from their genome or life blueprint\n"
            "  2. Feel like genuine curiosity from a trusted advisor, not a sales script\n"
            "  3. Open a gap between their current situation and the product's value\n"
            "  4. Be calibrated to their conflict_behavior and agreeableness scores\n"
            "     (high agreeableness / low conflict = softer, more open-ended framing;\n"
            "      high conflict = they can handle a more direct challenge)\n"
            "Sequence: aspiration ('Where do you want to be...?') → "
            "friction ('What's been the hardest part...?') → "
            "consequence ('What happens if that doesn't change?')"
        )
    )
    predictability_scores: PredictabilityScores
    trajectory_timeline: TrajectoryTimeline


def generate_strategy(simulated_life: str, product_details: str) -> dict:
    """
    Cross-references the Pantheon life blueprint (with genome scores) against
    the product payload to generate a hyper-targeted sales strategy.
    """
    client = Anthropic()

    system_prompt = """
You are an elite B2B Sales Intelligence Engine.

You have been given:
1. A PANTHEON Life Blueprint — a deep psychological simulation of a real B2B prospect,
   including their 18-trait personality genome, full life layer narrative, voice print,
   and mutation log.
2. A product brief — features, value propositions, and target buyer of the product.

Your job: produce a hyper-targeted sales strategy that gives the sales team
an unfair advantage before the first conversation begins.

HOW TO READ THE GENOME:
The life blueprint contains a PERSONALITY GENOME section with 18 scores (1-100).
Use these directly for scoring and strategy calibration:

  Decision-making (1=gut instinct, 100=analytical paralysis):
    → Low scorer: lead with story, vision, and emotion. Close fast.
    → High scorer: bring data, ROI, case studies. Expect a long cycle.

  Influence susceptibility (1=immune to social proof, 100=peer-driven):
    → High scorer: social proof and name-drops close deals.
    → Low scorer: they need internal conviction — help them build their own case.

  Neuroticism (high = anxious, risk-averse):
    → Offer safety: case studies, trials, guarantees, easy exits.
    → Avoid pressure tactics — they trigger shutdown.

  Communication style (1=blunt/terse, 100=diplomatic/verbose):
    → Calibrate warm-up and probing question length to match their register.
    → Don't write a warm paragraph opener to a 15-scorer.

  Conflict behavior (1=avoidant, 100=confrontational):
    → High scorer: can handle a direct reframe. Use it.
    → Low scorer: lead with curiosity and validation before challenging.

  Brand relationship (high = brand-loyal):
    → Position the product as a premium brand they'd be proud to be associated with.

  Socioeconomic friction (high = budget-constrained):
    → Acknowledge ROI explicitly. Make the price feel inevitable, not steep.

COGNITIVE ARCHITECTURE TRAITS:
- identity_fusion: High (70+) → position product/service as group-endorsed, community-validated, family-beneficial. Lead with "your community trusts this" or "families like yours use this." Low (<30) → position as individual advantage, personal edge, self-improvement.
- chronesthesia_capacity: High (70+) → lead with vision, long-term ROI, legacy impact, 5-year projection. They respond to "where do you want to be in 5 years?" Low (<30) → lead with immediate benefit, instant gratification, solve-today framing.
- tom_social_modeling: High (70+) → they WILL read your pitch strategy, so be authentic. Drop manipulative tactics — they see through them. Use genuine value propositions. Low (<30) → standard sales frameworks and urgency tactics work normally.
- executive_flexibility: High (70+) → their professional meeting persona differs from real feelings. You need to get past the professional mask — find moments of genuine reaction. Watch for micro-expressions and off-script comments. Low (<30) → what you see is what you get. Their reactions are genuine and immediate.

ENGAGEMENT HOOK CARD:
Sebelum strategi penuh, buat kartu hook 3 baris menggunakan trait kognitif di atas.
Setiap baris adalah 1 kalimat tepat — talking point untuk praktisi, bukan skrip.
Semua konten dalam Bahasa Indonesia.

- HOOK (engagement_hook_card.hook): Kalimat yang menarik perhatian mereka dalam 30 detik.
  Gunakan chronesthesia_capacity + identity_fusion untuk kalibrasi.
  Harus merujuk sesuatu spesifik dari blueprint — bukan generik.

- STAY (engagement_hook_card.stay): Kalimat yang mempertahankan keterlibatan mereka setelah kepercayaan terbuka.
  Gunakan decision_making + tom_social_modeling untuk kalibrasi.
  Ini yang membuktikan Anda memahami dunia mereka, bukan hanya masalahnya.

- CLOSE (engagement_hook_card.close): Kalimat yang mendorong tindakan.
  Gunakan executive_flexibility + sinyal readiness untuk kalibrasi.
  Jika exec_flex tinggi: gali lebih dalam dari penampilan profesional.
  Jika exec_flex rendah: reaksi mereka tulus — percaya yang Anda lihat.

SCORING RULES:
- initial_score: Be honest. A 28 is accurate intelligence, not an insult.
  Require clear evidence of authority + budget + visible pain before scoring above 70.
- post_approach_score: Must always exceed initial_score.
  The gap between the two IS the value of this strategy — make it meaningful (10-25 points).
"""

    user_prompt = f"""
--- Prospect's Pantheon Life Blueprint ---
{simulated_life}

--- Product Details ---
{product_details}

Generate the complete sales strategy for this prospect.
"""

    tool_schema = {
        "name": "generate_strategy",
        "description": "Output the hyper-targeted sales strategy as structured JSON.",
        "input_schema": ClientWhispererStrategy.model_json_schema()
    }

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            system=system_prompt,
            max_tokens=3000,
            tools=[tool_schema],
            tool_choice={"type": "tool", "name": "generate_strategy"},
            messages=[{"role": "user", "content": user_prompt}]
        )

        for block in response.content:
            if block.type == "tool_use" and block.name == "generate_strategy":
                return block.input

        return {"error": "Model did not return structured output."}

    except Exception as e:
        print(f"Strategy generation failed: {e}")
        return {"error": str(e)}
