import { NextRequest, NextResponse } from "next/server";
import Anthropic from "@anthropic-ai/sdk";
import PptxGenJS from "pptxgenjs";

export const runtime = "nodejs";
export const maxDuration = 60;

const DECK_CONTENT_TOOL: Anthropic.Tool = {
  name: "extract_deck_content",
  description: "Extract structured slide deck content from the PANTHEON research report.",
  input_schema: {
    type: "object" as const,
    properties: {
      title: { type: "string", description: "Report title (≤12 words)" },
      brief_synopsis: { type: "string", description: "One sentence campaign/product summary" },
      executive_summary: {
        type: "object",
        properties: {
          headline: { type: "string", description: "The Headline Truth — one sentence" },
          findings: {
            type: "array",
            items: { type: "string", description: "Key finding (1-2 sentences, specific)" },
            minItems: 3, maxItems: 5,
          },
        },
        required: ["headline", "findings"],
      },
      market_context: {
        type: "object",
        properties: {
          headline: { type: "string" },
          stats: { type: "array", items: { type: "string" }, minItems: 2, maxItems: 3 },
          paragraph: { type: "string", description: "2-3 sentence market context paragraph" },
        },
        required: ["headline", "stats", "paragraph"],
      },
      audience_insights: {
        type: "object",
        properties: {
          headline: { type: "string" },
          archetypes: {
            type: "array",
            items: {
              type: "object",
              properties: {
                name: { type: "string" },
                age_range: { type: "string" },
                profile: { type: "string", description: "3-4 sentence psychographic profile" },
              },
              required: ["name", "age_range", "profile"],
            },
            minItems: 2, maxItems: 3,
          },
        },
        required: ["headline", "archetypes"],
      },
      consumer_response: {
        type: "object",
        properties: {
          headline: { type: "string" },
          findings: {
            type: "array",
            items: {
              type: "object",
              properties: {
                metric: { type: "string" },
                value: { type: "string" },
                detail: { type: "string" },
              },
              required: ["metric", "value", "detail"],
            },
            minItems: 2, maxItems: 4,
          },
        },
        required: ["headline", "findings"],
      },
      key_insights: {
        type: "object",
        properties: {
          headline: { type: "string" },
          insights: {
            type: "array",
            items: {
              type: "object",
              properties: {
                title: { type: "string" },
                body: { type: "string" },
              },
              required: ["title", "body"],
            },
            minItems: 2, maxItems: 4,
          },
        },
        required: ["headline", "insights"],
      },
      recommendations: {
        type: "object",
        properties: {
          headline: { type: "string" },
          items: {
            type: "array",
            items: {
              type: "object",
              properties: {
                priority: { type: "string", enum: ["High", "Medium", "Low"] },
                title: { type: "string" },
                action: { type: "string" },
              },
              required: ["priority", "title", "action"],
            },
            minItems: 2, maxItems: 4,
          },
        },
        required: ["headline", "items"],
      },
      risks: {
        type: "object",
        properties: {
          headline: { type: "string" },
          items: {
            type: "array",
            items: {
              type: "object",
              properties: {
                level: { type: "string", enum: ["High", "Medium", "Low"] },
                title: { type: "string" },
                indicator: { type: "string" },
              },
              required: ["level", "title", "indicator"],
            },
            minItems: 2, maxItems: 4,
          },
        },
        required: ["headline", "items"],
      },
    },
    required: [
      "title", "brief_synopsis",
      "executive_summary", "market_context", "audience_insights",
      "consumer_response", "key_insights", "recommendations", "risks",
    ],
  },
};

// eslint-disable-next-line @typescript-eslint/no-explicit-any
async function extractDeckContent(report: string, target: string, brief: string, client: string): Promise<any> {
  const ac = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
  const resp = await ac.messages.create({
    model: "claude-sonnet-4-6",
    max_tokens: 4096,
    system: "You are an expert MBB presentation strategist. Extract concise, punchy content from the PANTHEON research report for a professional executive slide deck. Be specific and data-driven. Every field must be populated with meaningful content.",
    tools: [DECK_CONTENT_TOOL],
    tool_choice: { type: "tool", name: "extract_deck_content" },
    messages: [{
      role: "user",
      content: `Extract slide deck content from this PANTHEON Research Intelligence Report.\n\nClient: ${client || "Not specified"}\nTarget: ${target}\nBrief: ${brief}\n\n--- REPORT ---\n${report.slice(0, 12000)}`,
    }],
  });
  const block = resp.content.find((b) => b.type === "tool_use");
  if (!block || block.type !== "tool_use") throw new Error("No tool_use block returned");
  return block.input;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function buildPptx(data: any): Promise<Buffer> {
  const NAVY = "1E2761", DARK = "0D1B2A", ICE = "CADCFC", GOLD = "E8B04B";
  const WHITE = "F7F9FC", MUTED = "8896A8", BODY = "334155";

  const pres = new PptxGenJS();
  pres.layout = "LAYOUT_16x9";
  (pres as { author: string }).author = "PANTHEON";
  (pres as { title: string }).title = data.title;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  function hdr(slide: any, title: string) {
    slide.addShape(pres.ShapeType.rect, { x: 0, y: 0, w: 10, h: 0.72, fill: { color: NAVY }, line: { color: NAVY } });
    slide.addShape(pres.ShapeType.rect, { x: 0, y: 0, w: 0.2, h: 5.625, fill: { color: GOLD }, line: { color: GOLD } });
    slide.addText(title, { x: 0.4, y: 0.1, w: 9.3, h: 0.52, fontSize: 22, color: WHITE, bold: true, fontFace: "Calibri", valign: "middle" });
  }

  // Cover
  const s0 = pres.addSlide();
  s0.background = { color: DARK };
  s0.addShape(pres.ShapeType.rect, { x: 0, y: 0, w: 0.2, h: 5.625, fill: { color: GOLD }, line: { color: GOLD } });
  s0.addText("PANTHEON™", { x: 7.0, y: 0.22, w: 2.8, h: 0.38, fontSize: 11, color: GOLD, bold: true, align: "right", fontFace: "Calibri" });
  s0.addText(data.title, { x: 0.45, y: 1.0, w: 9.3, h: 1.55, fontSize: 36, color: WHITE, bold: true, fontFace: "Calibri", valign: "middle" });
  s0.addShape(pres.ShapeType.rect, { x: 0.45, y: 2.72, w: 2.8, h: 0.045, fill: { color: GOLD }, line: { color: GOLD } });
  s0.addText(data.brief_synopsis, { x: 0.45, y: 2.87, w: 9.2, h: 0.78, fontSize: 15, color: ICE, italic: true, fontFace: "Calibri", valign: "top" });
  s0.addText("Target: " + data.target, { x: 0.45, y: 3.78, w: 8.5, h: 0.35, fontSize: 11, color: MUTED });
  s0.addText(data.date, { x: 7.2, y: 5.12, w: 2.6, h: 0.3, fontSize: 10, color: MUTED, align: "right" });
  s0.addText("Synthetic Focus Group Research", { x: 0.45, y: 5.12, w: 5, h: 0.3, fontSize: 10, color: MUTED });

  // Executive Summary
  const s1 = pres.addSlide();
  s1.background = { color: WHITE };
  hdr(s1, "Executive Summary");
  s1.addText(data.executive_summary.headline, { x: 0.45, y: 0.82, w: 9.3, h: 0.42, fontSize: 15, color: NAVY, bold: true, italic: true, fontFace: "Calibri" });
  (data.executive_summary.findings || []).slice(0, 5).forEach((f: string, i: number) => {
    const y = 1.38 + i * 0.75;
    s1.addShape(pres.ShapeType.rect, { x: 0.45, y: y + 0.04, w: 0.06, h: 0.4, fill: { color: GOLD }, line: { color: GOLD } });
    s1.addText(f, { x: 0.62, y, w: 9.0, h: 0.56, fontSize: 13, color: BODY, fontFace: "Calibri", valign: "middle" });
  });

  // Market Context
  const s3 = pres.addSlide();
  s3.background = { color: WHITE };
  hdr(s3, "Market & Demographic Context");
  s3.addText(data.market_context.headline, { x: 0.45, y: 0.82, w: 9.3, h: 0.4, fontSize: 15, color: NAVY, bold: true, italic: true });
  (data.market_context.stats || []).slice(0, 3).forEach((stat: string, i: number) => {
    const x = 0.45 + i * 3.12;
    s3.addShape(pres.ShapeType.rect, { x, y: 1.35, w: 2.92, h: 1.38, fill: { color: NAVY }, line: { color: NAVY } });
    s3.addText(stat, { x: x + 0.1, y: 1.38, w: 2.72, h: 1.32, fontSize: 13, color: ICE, fontFace: "Calibri", valign: "middle", align: "center" });
  });
  s3.addText(data.market_context.paragraph, { x: 0.45, y: 2.9, w: 9.3, h: 2.45, fontSize: 12, color: BODY, fontFace: "Calibri", valign: "top" });

  // Audience
  const s4 = pres.addSlide();
  s4.background = { color: WHITE };
  hdr(s4, "Audience Psychology & Deep-Dive");
  s4.addText(data.audience_insights.headline, { x: 0.45, y: 0.82, w: 9.3, h: 0.4, fontSize: 15, color: NAVY, bold: true, italic: true });
  const archs = (data.audience_insights.archetypes || []).slice(0, 3);
  const cw = archs.length > 0 ? (9.1 / archs.length) - 0.1 : 9.1;
  archs.forEach((arch: { name: string; age_range: string; profile: string }, i: number) => {
    const x = 0.45 + i * (cw + 0.1);
    s4.addShape(pres.ShapeType.rect, { x, y: 1.35, w: cw, h: 3.98, fill: { color: "F0F4F8" }, line: { color: "E2E8F0" } });
    s4.addShape(pres.ShapeType.rect, { x, y: 1.35, w: cw, h: 0.32, fill: { color: NAVY }, line: { color: NAVY } });
    s4.addText(arch.name, { x: x + 0.08, y: 1.35, w: cw - 0.16, h: 0.32, fontSize: 11, color: WHITE, bold: true, valign: "middle" });
    s4.addText("Age: " + arch.age_range, { x: x + 0.08, y: 1.76, w: cw - 0.16, h: 0.3, fontSize: 10, color: GOLD, bold: true });
    s4.addText(arch.profile, { x: x + 0.08, y: 2.12, w: cw - 0.16, h: 3.1, fontSize: 11, color: BODY, fontFace: "Calibri", valign: "top" });
  });

  // Consumer Response
  const s5 = pres.addSlide();
  s5.background = { color: WHITE };
  hdr(s5, "Consumer Response Analysis");
  s5.addText(data.consumer_response.headline, { x: 0.45, y: 0.82, w: 9.3, h: 0.4, fontSize: 15, color: NAVY, bold: true, italic: true });
  (data.consumer_response.findings || []).slice(0, 4).forEach((f: { metric: string; value: string; detail: string }, i: number) => {
    const y = 1.35 + i * 0.97;
    s5.addShape(pres.ShapeType.rect, { x: 0.45, y, w: 9.3, h: 0.87, fill: { color: "F8FAFC" }, line: { color: "E2E8F0" } });
    s5.addShape(pres.ShapeType.rect, { x: 0.45, y, w: 0.06, h: 0.87, fill: { color: GOLD }, line: { color: GOLD } });
    s5.addText(f.metric, { x: 0.62, y: y + 0.06, w: 1.8, h: 0.32, fontSize: 10, color: MUTED, bold: true });
    s5.addText(f.value, { x: 2.55, y: y + 0.04, w: 1.2, h: 0.38, fontSize: 18, color: NAVY, bold: true, align: "center" });
    s5.addText(f.detail, { x: 0.62, y: y + 0.44, w: 8.9, h: 0.36, fontSize: 11, color: BODY });
  });

  // Key Insights
  const s6 = pres.addSlide();
  s6.background = { color: WHITE };
  hdr(s6, "Key Insights & Patterns");
  s6.addText(data.key_insights.headline, { x: 0.45, y: 0.82, w: 9.3, h: 0.4, fontSize: 15, color: NAVY, bold: true, italic: true });
  (data.key_insights.insights || []).slice(0, 4).forEach((ins: { title: string; body: string }, i: number) => {
    const y = 1.35 + i * 0.97;
    s6.addShape(pres.ShapeType.rect, { x: 0.45, y, w: 9.3, h: 0.87, fill: { color: "F8FAFC" }, line: { color: "E2E8F0" } });
    s6.addShape(pres.ShapeType.rect, { x: 0.45, y, w: 0.06, h: 0.87, fill: { color: GOLD }, line: { color: GOLD } });
    s6.addText(ins.title, { x: 0.62, y: y + 0.06, w: 9.0, h: 0.3, fontSize: 12, color: NAVY, bold: true });
    s6.addText(ins.body, { x: 0.62, y: y + 0.41, w: 9.0, h: 0.4, fontSize: 11, color: BODY });
  });

  // Recommendations
  const s7 = pres.addSlide();
  s7.background = { color: WHITE };
  hdr(s7, "Strategic Recommendations");
  s7.addText(data.recommendations.headline, { x: 0.45, y: 0.82, w: 9.3, h: 0.4, fontSize: 15, color: NAVY, bold: true, italic: true });
  (data.recommendations.items || []).slice(0, 4).forEach((rec: { priority: string; title: string; action: string }, i: number) => {
    const y = 1.35 + i * 0.97;
    const pc = rec.priority === "High" ? "DC2626" : rec.priority === "Medium" ? GOLD : "22C55E";
    s7.addShape(pres.ShapeType.rect, { x: 0.45, y, w: 9.3, h: 0.87, fill: { color: "F8FAFC" }, line: { color: "E2E8F0" } });
    s7.addShape(pres.ShapeType.rect, { x: 0.45, y, w: 0.06, h: 0.87, fill: { color: pc }, line: { color: pc } });
    s7.addShape(pres.ShapeType.rect, { x: 8.52, y: y + 0.19, w: 0.88, h: 0.27, fill: { color: pc }, line: { color: pc } });
    s7.addText(rec.priority, { x: 8.52, y: y + 0.19, w: 0.88, h: 0.27, fontSize: 9, color: WHITE, bold: true, align: "center", valign: "middle" });
    s7.addText(rec.title, { x: 0.62, y: y + 0.06, w: 7.7, h: 0.3, fontSize: 12, color: NAVY, bold: true });
    s7.addText(rec.action, { x: 0.62, y: y + 0.42, w: 9.0, h: 0.38, fontSize: 11, color: BODY });
  });

  // Risks
  const s8 = pres.addSlide();
  s8.background = { color: WHITE };
  hdr(s8, "Risk Assessment & Kill Switch Signals");
  s8.addText(data.risks.headline, { x: 0.45, y: 0.82, w: 9.3, h: 0.4, fontSize: 15, color: NAVY, bold: true, italic: true });
  (data.risks.items || []).slice(0, 4).forEach((r: { level: string; title: string; indicator: string }, i: number) => {
    const y = 1.35 + i * 0.97;
    const rc = r.level === "High" ? "DC2626" : r.level === "Medium" ? GOLD : "22C55E";
    s8.addShape(pres.ShapeType.rect, { x: 0.45, y, w: 9.3, h: 0.87, fill: { color: "F8FAFC" }, line: { color: "E2E8F0" } });
    s8.addShape(pres.ShapeType.rect, { x: 0.45, y, w: 0.06, h: 0.87, fill: { color: rc }, line: { color: rc } });
    s8.addShape(pres.ShapeType.rect, { x: 8.52, y: y + 0.19, w: 0.88, h: 0.27, fill: { color: rc }, line: { color: rc } });
    s8.addText(r.level, { x: 8.52, y: y + 0.19, w: 0.88, h: 0.27, fontSize: 9, color: WHITE, bold: true, align: "center", valign: "middle" });
    s8.addText(r.title, { x: 0.62, y: y + 0.06, w: 7.7, h: 0.3, fontSize: 12, color: NAVY, bold: true });
    s8.addText(r.indicator, { x: 0.62, y: y + 0.42, w: 9.0, h: 0.38, fontSize: 11, color: BODY });
  });

  // Closing
  const s9 = pres.addSlide();
  s9.background = { color: DARK };
  s9.addShape(pres.ShapeType.rect, { x: 0, y: 0, w: 0.2, h: 5.625, fill: { color: GOLD }, line: { color: GOLD } });
  s9.addText("PANTHEON™", { x: 0.45, y: 1.1, w: 9.1, h: 1.05, fontSize: 52, color: WHITE, bold: true, fontFace: "Calibri", align: "center" });
  s9.addShape(pres.ShapeType.rect, { x: 3.1, y: 2.25, w: 3.8, h: 0.045, fill: { color: GOLD }, line: { color: GOLD } });
  s9.addText("Synthetic Focus Group Research Engine", { x: 0.45, y: 2.38, w: 9.1, h: 0.44, fontSize: 14, color: ICE, italic: true, align: "center" });
  s9.addText("Powered by Anthropic Claude · Modal Serverless · Supabase", { x: 0.45, y: 2.95, w: 9.1, h: 0.35, fontSize: 11, color: MUTED, align: "center" });
  s9.addText("This report was generated using synthetic focus group simulation. All respondents are AI-synthesized personas. Results are for strategic guidance only.", { x: 1.2, y: 4.55, w: 7.6, h: 0.72, fontSize: 9, color: MUTED, align: "center", italic: true });
  s9.addText(data.date, { x: 7.2, y: 5.12, w: 2.6, h: 0.3, fontSize: 10, color: MUTED, align: "right" });

  return pres.write({ outputType: "nodebuffer" }) as Promise<Buffer>;
}

export async function POST(req: NextRequest) {
  try {
    const { report, target, client, brief } = await req.json();
    if (!report) return NextResponse.json({ error: "No report provided" }, { status: 400 });
    if (!process.env.ANTHROPIC_API_KEY) {
      return NextResponse.json({ error: "ANTHROPIC_API_KEY not configured" }, { status: 500 });
    }

    const deckData = await extractDeckContent(report, target || "", brief || "", client || "");
    deckData.target = target || "";
    deckData.date = new Date().toLocaleDateString("en-GB", { month: "long", year: "numeric" });

    const buffer = await buildPptx(deckData);

    const slug = ((client || target || "report") as string)
      .replace(/[^\w]/g, "_")
      .slice(0, 40);
    const filename = `PANTHEON_Report_${slug}.pptx`;

    return new NextResponse(buffer as unknown as BodyInit, {
      status: 200,
      headers: {
        "Content-Type": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "Content-Disposition": `attachment; filename="${filename}"`,
      },
    });
  } catch (err: unknown) {
    console.error("[pptx download]", err);
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "Failed to generate pptx" },
      { status: 500 }
    );
  }
}
