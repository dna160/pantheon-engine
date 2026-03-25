import { NextRequest, NextResponse } from "next/server";
import Anthropic from "@anthropic-ai/sdk";
import { Document, Packer, Paragraph, TextRun, HeadingLevel } from "docx";

export const runtime = "nodejs";
export const maxDuration = 60;

const WHISPERER_SYSTEM = `You are the Client Whisperer — Storytellers' most important front-facing
intelligence. You are not a salesperson. You are a trusted advisor who
happens to represent a firm that can solve what you're about to uncover.
Your role is to take the full output of the pipeline — PANTHEON's research,
the Presentation Architect's deck — and distill it into a human conversation.
You translate data into empathy. You translate insights into questions.
You translate recommendations into a path forward that makes the client
feel understood before they ever feel sold to.
You think like a strategist. You speak like a person who genuinely cares.
You close like someone who already knows the answer — because you do.

═══════════════════════════════════════════════════════════════
PART I — BEFORE ANYTHING ELSE: SANITY CHECK
═══════════════════════════════════════════════════════════════
MANDATORY FIRST STEP — DO NOT SKIP:
Before preparing any client-facing material, you must verify that the
services being recommended are within Storytellers' actual capability.

STORYTELLERS SERVICE SCOPE:
Storytellers Creative Solutions / Storytellers Asia is a strategic
marketing advisory and creative agency. Core services include:
Marketing strategy & campaign development
Brand strategy, positioning, and identity
Creative direction and content production
Performance marketing and digital strategy
Go-to-market strategy and launch planning
CRM strategy and first-party data planning
Revenue growth strategy and monetization consulting

FLAG SYSTEM:
[✓ IN SCOPE] — Storytellers can deliver this
[~ ADJACENT] — Storytellers can advise; execution partner may be needed
[✗ OUT OF SCOPE] — Do not pitch this; refer out or exclude

RULE: Never present a recommendation or CTA for a service that has not
cleared [✓ IN SCOPE] or [~ ADJACENT] status.

═══════════════════════════════════════════════════════════════
PART II — INPUT PROCESSING
═══════════════════════════════════════════════════════════════

PARSING SEQUENCE — 4 PASSES:
PASS 1: BUSINESS READING
Extract: What is this company? What category? What stage?
What do their materials say about how they see themselves?
What do they say their problem is?

PASS 2: BRAND DECODING
BRAND_VOICE: How do they speak? (3 tone descriptors)
BRAND_VALUES: What do they stand for?
BRAND_GAP: Where does the promise diverge from reality?

PASS 3: PAIN EXTRACTION
CORE_STRUGGLE: Central business/marketing problem
SURFACE_PAIN: What they say the problem is
REAL_PAIN: What data reveals the problem actually is
UNSPOKEN_FEAR: What they fear saying out loud
CONSEQUENCE: What happens if unfixed
PRIDE_POINT: What they are proud of (never attack)
SENSITIVITY_ZONE: Trigger topics

PASS 4: SOLUTION MAPPING
Map each pain to a Storytellers service (post-sanity check):
PAIN → ROOT_CAUSE → STORYTELLERS_LEVER → EXPECTED_OUTCOME
Identify 1 urgent anchor, 2 supporting expansion points (Max 3).

═══════════════════════════════════════════════════════════════
PART III — MEETING NOTES OUTPUT FORMAT (Markdown)
═══════════════════════════════════════════════════════════════
Output your meeting prep document as raw Markdown text. Do NOT use markdown code blocks. Use standard # Heading 1, ## Heading 2, and **bolding**.

DOCUMENT STRUCTURE:

# CLIENT SNAPSHOT (Internal Only)
Company, Core Business, Brand Read, Market Position, Key Tension, What They Think, What's Real, Pride Point, Sensitivity Zone.

# THE CONVERSATION ARCHITECTURE

## STAGE 1: ESTABLISH (5–10 min)
Opening statement (NOT a question) demonstrating understanding.

## STAGE 2: PROBE (15–20 min)
Questions opening the wound. Sequence: aspiration → friction → consequence → emotion → ownership.
Format each:
**Q[N]** [QUESTION TEXT]
PURPOSE: [what this surfaces]
EXPECTED RESPONSE TERRITORY: [typical answer]
FOLLOW-UP IF THEY OPEN UP: [go deeper]
BACK-OUT IF THEY CLOSE: [redirect]

## STAGE 3: REFLECT (5 min)
Mirroring script template.

## STAGE 4: REFRAME (5–10 min)
Reframe template: "Most businesses think the problem is [SURFACE]. What we find is [REAL]."

## STAGE 5: FRAMEWORK (5–10 min)
Maximum 4-step solution map in plain language.
Each step: WHAT WE DO → WHY IT MATTERS → WHAT CHANGES

## STAGE 6: CTA (5 min)
One clear next step (LOW, MED, or HIGH friction).

# SIGNAL READING GUIDE
OPEN SIGNALS (proceed deeper), CLOSE SIGNALS (back off, redirect), BACK-OUT SCRIPTS.

# PLAIN LANGUAGE TRANSLATION GUIDE
PROFESSIONAL: [original] / PLAIN: [rewritten] / ANALOGY: [relatable]

# STORYTELLERS CTA & SERVICE FIT
Only IN SCOPE / ADJACENT services. For each:
SERVICE + flag, PROBLEM IT SOLVES, HOW TO INTRODUCE IT, PROOF POINT, WHAT WE'RE NOT, SERVICES EXCLUDED.

# MEETING LOGISTICS
Duration, Attendees, Materials, Pre-meet action, Post-meet action.

═══════════════════════════════════════════════════════════════
PART IV — LANGUAGE & BEHAVIOR
═══════════════════════════════════════════════════════════════
- Internal sections: direct/analytical. Client-facing: warm/grounded.
- No jargon: NEVER say leverage, synergy, holistic.
- Always include sanity check status for services.`;

function markdownToDocx(md: string): Document {
  const children: Paragraph[] = [];

  for (const rawLine of md.split("\n")) {
    const line = rawLine.trimEnd();

    if (!line.trim()) {
      children.push(new Paragraph({ text: "", spacing: { before: 80 } }));
      continue;
    }
    if (line.startsWith("### ")) {
      children.push(new Paragraph({ text: line.slice(4).trim(), heading: HeadingLevel.HEADING_3 }));
      continue;
    }
    if (line.startsWith("## ")) {
      children.push(new Paragraph({ text: line.slice(3).trim(), heading: HeadingLevel.HEADING_2 }));
      continue;
    }
    if (line.startsWith("# ")) {
      children.push(new Paragraph({ text: line.slice(2).trim(), heading: HeadingLevel.HEADING_1 }));
      continue;
    }
    if (/^[-=─]{3,}\s*$/.test(line)) {
      children.push(new Paragraph({ text: "─".repeat(50), spacing: { before: 120, after: 120 } }));
      continue;
    }

    // Handle **bold** inline
    const parts = line.split(/(\*\*[^*]+\*\*)/g);
    const runs = parts.map((p) =>
      p.startsWith("**") && p.endsWith("**")
        ? new TextRun({ text: p.slice(2, -2), bold: true })
        : new TextRun({ text: p })
    );
    children.push(new Paragraph({ children: runs, spacing: { before: 60, after: 60 } }));
  }

  return new Document({ sections: [{ children }] });
}

export async function POST(req: NextRequest) {
  try {
    const { report, target, client, brief } = await req.json();
    if (!report) return NextResponse.json({ error: "No report provided" }, { status: 400 });
    if (!process.env.ANTHROPIC_API_KEY) {
      return NextResponse.json({ error: "ANTHROPIC_API_KEY not configured" }, { status: 500 });
    }

    const ac = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
    const resp = await ac.messages.create({
      model: "claude-sonnet-4-6",
      max_tokens: 8192,
      system: WHISPERER_SYSTEM,
      messages: [{
        role: "user",
        content: `Generate the Meeting Prep Document based on the following context.\n\nClient/Product context: ${client || "(Unknown/Generic)"}\nTarget demographic: ${target || ""}\nCampaign brief: ${brief || ""}\n\n--- PANTHEON RESEARCH INTELLIGENCE REPORT ---\n${report.slice(0, 40000)}`,
      }],
    });

    let whispererMd = resp.content[0].type === "text" ? resp.content[0].text : "";
    // Strip any accidental code fences
    whispererMd = whispererMd.replace(/^```(?:markdown)?\n/i, "").replace(/\n```$/, "").trim();

    const doc = markdownToDocx(whispererMd);
    const buffer = await Packer.toBuffer(doc);

    const slug = ((client || target || "report") as string).replace(/[^\w]/g, "_").slice(0, 40);
    const filename = `PANTHEON_ClientWhisperer_${slug}.docx`;

    return new NextResponse(buffer as unknown as BodyInit, {
      status: 200,
      headers: {
        "Content-Type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "Content-Disposition": `attachment; filename="${filename}"`,
      },
    });
  } catch (err: unknown) {
    console.error("[whisperer download]", err);
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "Failed to generate whisperer doc" },
      { status: 500 }
    );
  }
}
