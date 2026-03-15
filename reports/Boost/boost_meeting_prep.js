const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, HeadingLevel, BorderStyle, WidthType, ShadingType,
  VerticalAlign, PageNumber, PageBreak, LevelFormat, Header, Footer
} = require('docx');
const fs = require('fs');

// ─── PALETTE ───────────────────────────────────────────────
const NAVY      = "1B3A5C";
const GOLD      = "C9A84C";
const STEEL     = "3A6186";
const RED       = "B03030";
const LIGHT_BG  = "EEF3F8";
const WARN_BG   = "FEF5E8";
const RISK_BG   = "FCEAEA";
const GREEN_BG  = "EAF5EA";
const RULE      = "C8D6E5";
const DARK      = "1A1A2E";
const MID       = "444455";
const BODY_FONT = "Calibri";
const HEAD_FONT = "Calibri";

// ─── DXA CONSTANTS ─────────────────────────────────────────
const PAGE_W    = 12240;
const MARGIN    = 1440;
const CONTENT_W = PAGE_W - MARGIN * 2; // 9360

// ─── BORDERS ───────────────────────────────────────────────
function cellBorder(color) {
  const b = { style: BorderStyle.SINGLE, size: 1, color: color || RULE };
  return { top: b, bottom: b, left: b, right: b };
}
function noBorder() {
  const b = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
  return { top: b, bottom: b, left: b, right: b };
}
function bottomBorderOnly(color, sz) {
  return {
    top: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
    bottom: { style: BorderStyle.SINGLE, size: sz || 4, color: color || RULE },
    left: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
    right: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" }
  };
}

// ─── HELPER: PARAGRAPH BUILDERS ────────────────────────────
function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 360, after: 120 },
    children: [new TextRun({ text, font: HEAD_FONT, size: 32, bold: true, color: NAVY })]
  });
}
function h2(text, color) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 280, after: 100 },
    children: [new TextRun({ text, font: HEAD_FONT, size: 26, bold: true, color: color || STEEL })]
  });
}
function h3(text, color) {
  return new Paragraph({
    spacing: { before: 200, after: 80 },
    children: [new TextRun({ text, font: HEAD_FONT, size: 22, bold: true, color: color || DARK })]
  });
}
function body(text, opts) {
  opts = opts || {};
  return new Paragraph({
    spacing: { before: 60, after: 80 },
    children: [new TextRun({
      text,
      font: BODY_FONT,
      size: opts.size || 20,
      bold: opts.bold || false,
      italic: opts.italic || false,
      color: opts.color || DARK
    })]
  });
}
function bodyItalic(text, color) {
  return new Paragraph({
    spacing: { before: 60, after: 60 },
    children: [new TextRun({ text: `"${text}"`, font: BODY_FONT, size: 20, italic: true, color: color || MID })]
  });
}
function spacer(before) {
  return new Paragraph({ spacing: { before: before || 120, after: 0 }, children: [new TextRun("")] });
}
function rule() {
  return new Paragraph({
    spacing: { before: 160, after: 160 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: RULE, space: 1 } },
    children: [new TextRun("")]
  });
}
function sectionDivider(label) {
  return new Paragraph({
    spacing: { before: 400, after: 200 },
    border: {
      bottom: { style: BorderStyle.SINGLE, size: 8, color: NAVY, space: 1 }
    },
    children: [new TextRun({ text: label.toUpperCase(), font: HEAD_FONT, size: 22, bold: true, color: NAVY, allCaps: true })]
  });
}

// ─── HELPER: BULLET ───────────────────────────────────────
function bullet(text, indent, bold, color) {
  return new Paragraph({
    spacing: { before: 40, after: 60 },
    numbering: { reference: "bullets", level: indent || 0 },
    children: [new TextRun({ text, font: BODY_FONT, size: 20, bold: bold || false, color: color || DARK })]
  });
}
function bullet2(runs) {
  return new Paragraph({
    spacing: { before: 40, after: 60 },
    numbering: { reference: "bullets", level: 0 },
    children: runs
  });
}
function subBullet(text) {
  return new Paragraph({
    spacing: { before: 30, after: 40 },
    numbering: { reference: "sub-bullets", level: 0 },
    children: [new TextRun({ text, font: BODY_FONT, size: 20, color: MID })]
  });
}
function numbered(text) {
  return new Paragraph({
    spacing: { before: 40, after: 60 },
    numbering: { reference: "numbers", level: 0 },
    children: [new TextRun({ text, font: BODY_FONT, size: 20, color: DARK })]
  });
}

// ─── HELPER: CALLOUT TABLES ───────────────────────────────
function calloutBox(label, lines, bgColor, borderColor) {
  const rows = [];
  // Header row
  rows.push(new TableRow({
    children: [new TableCell({
      borders: cellBorder(borderColor || STEEL),
      width: { size: CONTENT_W, type: WidthType.DXA },
      shading: { fill: borderColor ? borderColor.replace(/^/, '') : NAVY, type: ShadingType.CLEAR },
      margins: { top: 80, bottom: 80, left: 180, right: 180 },
      children: [new Paragraph({
        children: [new TextRun({ text: label.toUpperCase(), font: HEAD_FONT, size: 18, bold: true, color: "FFFFFF", allCaps: true })]
      })]
    })]
  }));
  // Content rows
  lines.forEach(line => {
    if (line === null) return;
    rows.push(new TableRow({
      children: [new TableCell({
        borders: cellBorder(borderColor || STEEL),
        width: { size: CONTENT_W, type: WidthType.DXA },
        shading: { fill: bgColor || LIGHT_BG, type: ShadingType.CLEAR },
        margins: { top: 80, bottom: 80, left: 180, right: 180 },
        children: [new Paragraph({
          spacing: { before: 40, after: 40 },
          children: typeof line === 'string'
            ? [new TextRun({ text: line, font: BODY_FONT, size: 20, color: DARK })]
            : line
        })]
      })]
    }));
  });
  return new Table({
    width: { size: CONTENT_W, type: WidthType.DXA },
    columnWidths: [CONTENT_W],
    rows
  });
}

function twoColTable(rows_data, col1, col2, headerFill) {
  const tableRows = rows_data.map((row, idx) => {
    const isHeader = idx === 0;
    return new TableRow({
      children: row.map((cell, ci) => new TableCell({
        borders: cellBorder(RULE),
        width: { size: ci === 0 ? col1 : col2, type: WidthType.DXA },
        shading: { fill: isHeader ? (headerFill || NAVY) : (idx % 2 === 0 ? LIGHT_BG : "FFFFFF"), type: ShadingType.CLEAR },
        margins: { top: 80, bottom: 80, left: 160, right: 160 },
        children: [new Paragraph({
          children: [new TextRun({
            text: cell,
            font: BODY_FONT,
            size: 20,
            bold: isHeader,
            color: isHeader ? "FFFFFF" : DARK
          })]
        })]
      }))
    });
  });
  return new Table({
    width: { size: CONTENT_W, type: WidthType.DXA },
    columnWidths: [col1, col2],
    rows: tableRows
  });
}

function threeColTable(rows_data, col1, col2, col3, headerFill) {
  const tableRows = rows_data.map((row, idx) => {
    const isHeader = idx === 0;
    return new TableRow({
      children: row.map((cell, ci) => {
        const w = ci === 0 ? col1 : ci === 1 ? col2 : col3;
        return new TableCell({
          borders: cellBorder(RULE),
          width: { size: w, type: WidthType.DXA },
          shading: { fill: isHeader ? (headerFill || NAVY) : (idx % 2 === 0 ? LIGHT_BG : "FFFFFF"), type: ShadingType.CLEAR },
          margins: { top: 80, bottom: 80, left: 140, right: 140 },
          children: [new Paragraph({
            children: [new TextRun({
              text: cell,
              font: BODY_FONT,
              size: isHeader ? 18 : 19,
              bold: isHeader,
              color: isHeader ? "FFFFFF" : DARK
            })]
          })]
        });
      })
    });
  });
  return new Table({
    width: { size: CONTENT_W, type: WidthType.DXA },
    columnWidths: [col1, col2, col3],
    rows: tableRows
  });
}

// ─── LABEL + VALUE INLINE PARAGRAPH ──────────────────────
function kv(label, value, valueColor) {
  return new Paragraph({
    spacing: { before: 60, after: 60 },
    children: [
      new TextRun({ text: `${label}:  `, font: BODY_FONT, size: 20, bold: true, color: NAVY }),
      new TextRun({ text: value, font: BODY_FONT, size: 20, color: valueColor || DARK })
    ]
  });
}

// ─── PAGE BREAK ───────────────────────────────────────────
function pageBreak() {
  return new Paragraph({ children: [new PageBreak()] });
}

// ═══════════════════════════════════════════════════
//  BUILD DOCUMENT
// ═══════════════════════════════════════════════════

const children = [];

// ─── COVER ───────────────────────────────────────────────
children.push(spacer(600));
children.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { before: 0, after: 40 },
  children: [new TextRun({ text: "STORYTELLERS", font: HEAD_FONT, size: 28, bold: true, color: GOLD, allCaps: true, characterSpacing: 200 })]
}));
children.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { before: 0, after: 200 },
  children: [new TextRun({ text: "STRATEGIC ADVISORY", font: HEAD_FONT, size: 20, color: MID, allCaps: true, characterSpacing: 100 })]
}));
children.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { before: 0, after: 80 },
  children: [new TextRun({ text: "CLIENT MEETING PREP", font: HEAD_FONT, size: 44, bold: true, color: NAVY, allCaps: true })]
}));
children.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { before: 0, after: 60 },
  children: [new TextRun({ text: "BOOST  —  The Urban Pulse", font: HEAD_FONT, size: 32, bold: true, color: GOLD })]
}));
children.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { before: 120, after: 60 },
  children: [new TextRun({ text: "Meeting Date: 6 March 2026   |   Classification: Internal Only", font: BODY_FONT, size: 20, italic: true, color: MID })]
}));
children.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { before: 40, after: 40 },
  children: [new TextRun({ text: "Prepared by: Client Whisperer Agent  |  Intelligence Source: PANTHEON-01", font: BODY_FONT, size: 18, italic: true, color: MID })]
}));
children.push(spacer(200));
children.push(rule());
children.push(spacer(100));

// Cover sanity summary strip
children.push(calloutBox(
  "SANITY CHECK — SCOPE CLEARED",
  [
    "[✓ IN SCOPE]   Campaign repositioning + creative direction (consequence imagery)",
    "[✓ IN SCOPE]   Go-to-market strategy — regional sub-campaign (Surabaya / Bandung / Medan / Semarang)",
    "[✓ IN SCOPE]   Brand narrative — Boost Access Program framing",
    "[~ ADJACENT]  CRM & retention narrative strategy — Evidence Vault messaging architecture (Storytellers owns the narrative; app build is client-side)",
    "[~ ADJACENT]  Revenue/monetization consulting — price tiering rationale and dignity framing",
    "[✗ OUT OF SCOPE]   App / product development — Evidence Vault technical build (refer to client product team or technology partner)",
  ],
  GREEN_BG,
  "2E7D32"
));

children.push(pageBreak());

// ═══════════════════════════════════════════════════
// SECTION 1: CLIENT SNAPSHOT
// ═══════════════════════════════════════════════════
children.push(sectionDivider("SECTION 1  —  CLIENT SNAPSHOT"));
children.push(body("Internal only. Read this before you walk into the room.", { italic: true, color: MID }));
children.push(spacer());

children.push(twoColTable([
  ["FIELD", "READ"],
  ["Company", "Boost — functional cold-pressed juice, Indonesia"],
  ["Category", "Functional Nutrition / Cold-Pressed Juice"],
  ["Stage", "Pre-launch / launch planning — campaign is brief-complete, execution pending"],
  ["Core Business", "Premium performance juice formulated around need-states (AM REVIVE, BRAIN POWER, RECOVERY PRO) with active compound science (nitrates, enzymes)"],
  ["Brand Read", "Voice: Driven, Scientific, Aesthetic  |  Values: Performance, Transparency, Urban Sophistication"],
  ["Market Position", "Challenger — entering a market of generic 'organic' juices with a science-first positioning play"],
  ["Key Tension", "The brand is selling class aspiration disguised as functional science — and the consumers who want it most are calculating whether they can afford to perform the identity it offers"],
  ["What They Think", "\"We need better awareness and education so people understand what the product actually does\""],
  ["What's Real", "The campaign is selling shame relief to people who can't sustainably afford the relief — and the retention mechanic (Boost Streak) is engineering detractors from its most enthusiastic early buyers"],
  ["Pride Point", "The science is real. AM REVIVE / BRAIN POWER / RECOVERY PRO is genuinely smart product architecture. Never attack this — build on it."],
  ["Sensitivity Zone", "Pricing strategy and accessibility. Any implication that the brand is 'predatory' or 'exploitative of aspiration' will trigger immediate defensiveness."],
], 2400, 6960));

children.push(spacer(200));

children.push(h3("THE ONE THING TO UNDERSTAND BEFORE YOU WALK IN", RED));
children.push(calloutBox(
  "The Kill Switch",
  [
    "Your most enthusiastic early adopter — the 22-26 year-old Jakarta professional stretching her budget to signal she's 'the type of person who succeeds' — is your highest-risk detractor.",
    "Month 1: she buys with pride. Month 3: a family expense hits. She breaks the streak. She feels like a fraud. Then she picks up her phone and writes a TikTok thread: 'I spent 2.1 million rupiah on Boost in 8 weeks. Here is what I gave up. Here is what the brand knew and didn't tell you.'",
    "Estimated reach: 2–5 million impressions within 72 hours. Impact: -60% trial intent among core PTM. She has receipts. She has insider status. She cannot be dismissed. And the shame-to-rage conversion in this demographic is violent.",
    "This is not hypothetical. The data shows it is already loading.",
  ],
  RISK_BG,
  RED
));

children.push(pageBreak());

// ═══════════════════════════════════════════════════
// SECTION 2: CONVERSATION ARCHITECTURE
// ═══════════════════════════════════════════════════
children.push(sectionDivider("SECTION 2  —  THE CONVERSATION ARCHITECTURE"));
children.push(body("This is the meeting script in disguise. Run it as a conversation, not a presentation.", { italic: true, color: MID }));
children.push(spacer(80));

// STAGE 1
children.push(h2("STAGE 1 — ESTABLISH  (5–10 min)", NAVY));
children.push(body("Purpose: Show you have done the work before asking a single question. Make them feel understood. This earns everything that follows."));
children.push(spacer(80));
children.push(h3("Opening Statement — say this, verbatim or close to it:"));
children.push(calloutBox(
  "Opening",
  [
    "From what we've been looking at, Boost is sitting in a really specific moment. You've built something with genuine science behind it — the need-state architecture is sharp, and the active compound education is actually doing something most brands in this category won't touch. But there's a gap between what the campaign is promising and what the people who want it most are actually experiencing. And that gap is quiet right now. It won't stay quiet. That's why we wanted to sit down.",
  ],
  LIGHT_BG,
  STEEL
));
children.push(spacer(80));
children.push(body("Watch for: a lean-forward, a \"yes exactly,\" or a shift in posture. That's your green light to move into Stage 2."));
children.push(spacer(100));

// STAGE 2
children.push(h2("STAGE 2 — PROBE  (15–20 min)", NAVY));
children.push(body("Purpose: Open the real conversation. Start safe. Go deeper on every signal of openness. Back out on every signal of closure."));
children.push(spacer(80));

// Q1
children.push(h3("Q1  —  ASPIRATION ANCHOR"));
children.push(calloutBox("Question",
  ["When you imagine Boost six months from launch — what does success look like for you? Not the KPIs, the feeling."],
  LIGHT_BG, STEEL));
children.push(body("Purpose: Establish their emotional investment. Gets them talking about what they care about before you introduce any tension.", { italic: true, color: MID }));
children.push(body("Expected territory: \"We want to be the brand people associate with serious performance\" / \"We want to be everywhere — gyms, offices\" / \"We want the product to sell itself.\"", { italic: true, color: MID }));
children.push(bullet2([new TextRun({ text: "Follow-up if they open up: ", font: BODY_FONT, size: 20, bold: true, color: NAVY }), new TextRun({ text: "\"What would that mean for the business specifically?\"", font: BODY_FONT, size: 20, italic: true, color: DARK })]));
children.push(bullet2([new TextRun({ text: "Back-out if they close: ", font: BODY_FONT, size: 20, bold: true, color: NAVY }), new TextRun({ text: "\"No need to go into detail — just trying to understand what matters most to the team right now.\"", font: BODY_FONT, size: 20, italic: true, color: DARK })]));
children.push(spacer(100));

// Q2
children.push(h3("Q2  —  TARGET REALITY CHECK"));
children.push(calloutBox("Question",
  ["When you picture the person most likely to buy Boost in the first 60 days — who is she? And what's she actually dealing with on a Tuesday afternoon?"],
  LIGHT_BG, STEEL));
children.push(body("Purpose: Test how accurately they know their buyer. Surface the gap between the aspirational PTM they've imagined and the anxious striver actually reaching for the product.", { italic: true, color: MID }));
children.push(body("Expected territory: Confident description of a polished 25-year-old analyst — slightly idealized.", { italic: true, color: MID }));
children.push(bullet2([new TextRun({ text: "Follow-up: ", font: BODY_FONT, size: 20, bold: true, color: NAVY }), new TextRun({ text: "\"Is she buying because of what the product does, or because of what buying it says about her?\"", font: BODY_FONT, size: 20, italic: true, color: DARK })]));
children.push(bullet2([new TextRun({ text: "Back-out: ", font: BODY_FONT, size: 20, bold: true, color: NAVY }), new TextRun({ text: "\"Fair — let me come at that differently.\"", font: BODY_FONT, size: 20, italic: true, color: DARK })]));
children.push(spacer(100));

// Q3
children.push(h3("Q3  —  CAMPAIGN PRESSURE TEST"));
children.push(calloutBox("Question",
  ["The deskscape visuals — the MacBook, the bottle, the clean aesthetic — what is that supposed to do for someone who sees it for the first time?"],
  LIGHT_BG, STEEL));
children.push(body("Purpose: Gets them to articulate the aspirational visual strategy themselves — then you can reflect back what the data shows it actually does.", { italic: true, color: MID }));
children.push(body("Expected territory: \"Signals premium, builds aspiration, positions us alongside brands like Equinox.\"", { italic: true, color: MID }));
children.push(bullet2([new TextRun({ text: "Follow-up: ", font: BODY_FONT, size: 20, bold: true, color: NAVY }), new TextRun({ text: "\"And for someone who doesn't quite feel like she's arrived yet — what does it do for her?\"", font: BODY_FONT, size: 20, italic: true, color: DARK })]));
children.push(bullet2([new TextRun({ text: "Back-out: ", font: BODY_FONT, size: 20, bold: true, color: NAVY }), new TextRun({ text: "\"No wrong answer — genuinely curious how you think about the visual role.\"", font: BODY_FONT, size: 20, italic: true, color: DARK })]));
children.push(spacer(100));

// Q4
children.push(h3("Q4  —  GAMIFICATION INTENT"));
children.push(calloutBox("Question",
  ["The Boost Streak — walk me through the thinking. What behaviour was it designed to drive?"],
  LIGHT_BG, STEEL));
children.push(body("Purpose: Let them explain the mechanism. Then you can surface the unintended consequence without it feeling like an attack.", { italic: true, color: MID }));
children.push(body("Expected territory: \"Habit formation, ClassPass-style retention, daily engagement loop.\"", { italic: true, color: MID }));
children.push(bullet2([new TextRun({ text: "Follow-up: ", font: BODY_FONT, size: 20, bold: true, color: NAVY }), new TextRun({ text: "\"What happens to the user who breaks the streak?\"", font: BODY_FONT, size: 20, italic: true, color: DARK })]));
children.push(bullet2([new TextRun({ text: "Back-out: ", font: BODY_FONT, size: 20, bold: true, color: NAVY }), new TextRun({ text: "\"Got it — let's set that aside and come back to it later.\"", font: BODY_FONT, size: 20, italic: true, color: DARK })]));
children.push(spacer(100));

// Q5
children.push(h3("Q5  —  GEOGRAPHY ASSUMPTION"));
children.push(calloutBox("Question",
  ["Is the campaign designed primarily for Jakarta, or are you trying to land it across the major metros?"],
  LIGHT_BG, STEEL));
children.push(body("Purpose: Surface the Jakarta-centrism assumption. Opens the door to the regional sub-campaign conversation.", { italic: true, color: MID }));
children.push(body("Expected territory: Either \"Jakarta first, then expand\" or \"All metros simultaneously\" — both create the opening.", { italic: true, color: MID }));
children.push(bullet2([new TextRun({ text: "Follow-up: ", font: BODY_FONT, size: 20, bold: true, color: NAVY }), new TextRun({ text: "\"The '3 PM meeting' urgency — does that land the same way in Semarang as it does in Jakarta?\"", font: BODY_FONT, size: 20, italic: true, color: DARK })]));
children.push(spacer(100));

// Q6
children.push(h3("Q6  —  FRICTION PROBE"));
children.push(calloutBox("Question",
  ["What's been the hardest part of getting this campaign to where it is? Not tactically — I mean the conversation that was difficult to have inside the team."],
  LIGHT_BG, STEEL));
children.push(body("Purpose: Surfaces internal tension. Often where the real problem lives. This is the question that changes the meeting.", { italic: true, color: MID }));
children.push(body("Expected territory: Pricing debate, science vs. lifestyle balance, pressure from above to move fast.", { italic: true, color: MID }));
children.push(bullet2([new TextRun({ text: "Follow-up: ", font: BODY_FONT, size: 20, bold: true, color: NAVY }), new TextRun({ text: "\"How did you land on the decision you made?\"", font: BODY_FONT, size: 20, italic: true, color: DARK })]));
children.push(bullet2([new TextRun({ text: "Back-out: ", font: BODY_FONT, size: 20, bold: true, color: NAVY }), new TextRun({ text: "\"Fair. Let me ask it differently — what would you do differently if you had another month?\"", font: BODY_FONT, size: 20, italic: true, color: DARK })]));
children.push(spacer(100));

// Q7
children.push(h3("Q7  —  CONSEQUENCE QUESTION"));
children.push(calloutBox("Question",
  ["If the campaign lands the way it's currently designed — and it builds a strong early following — what does the retention picture look like in month four?"],
  LIGHT_BG, STEEL));
children.push(body("Purpose: Makes them think through the medium-term consequence of current design. Plants the detractor seed without naming it directly.", { italic: true, color: MID }));
children.push(bullet2([new TextRun({ text: "Follow-up: ", font: BODY_FONT, size: 20, bold: true, color: NAVY }), new TextRun({ text: "\"What about the customer who bought enthusiastically but can't maintain the habit — daily purchase at that price point isn't sustainable for everyone in the target cohort. Where does she go?\"", font: BODY_FONT, size: 20, italic: true, color: DARK })]));
children.push(spacer(100));

// Q8
children.push(h3("Q8  —  EMOTIONAL CLOSE"));
children.push(calloutBox("Question",
  ["How confident are you — personally, not the team — that the campaign as designed will get you to where you said success feels like?"],
  LIGHT_BG, STEEL));
children.push(body("Purpose: Creates the space for honest doubt. This is where they often say what they've been thinking but not saying out loud.", { italic: true, color: MID }));
children.push(body("Expected territory: Either genuine confidence (high openness to pushing further) or a qualifier (\"mostly, but...\") — the qualifier is your opening.", { italic: true, color: MID }));
children.push(spacer(100));

// Q9
children.push(h3("Q9  —  OWNERSHIP CLOSE"));
children.push(calloutBox("Question",
  ["Do you feel like you have the right team around you to handle what comes up after launch — the retention piece, the regional rollout, the data from the web app?"],
  LIGHT_BG, STEEL));
children.push(body("Purpose: Surfaces gaps in capability or confidence. Direct precursor to the Storytellers CTA.", { italic: true, color: MID }));
children.push(spacer(100));
children.push(rule());

// STAGE 3
children.push(h2("STAGE 3 — REFLECT  (5 min)", NAVY));
children.push(body("Purpose: Mirror it back. Not a summary — a validation. This single moment is worth more than any slide."));
children.push(spacer(80));
children.push(calloutBox("Reflect Script",
  [
    "\"So if I'm hearing you right — you've built a product with genuine science behind it, you've designed a campaign that positions it beautifully in the premium space, and you're heading into launch with a lot of momentum. But underneath that, there's a question you're probably not saying out loud yet: what happens when the people you've worked hardest to attract find out they can't actually sustain what buying into this brand asks of them? Because that's not a creative problem. That's a much more solvable problem than it looks. Does that feel accurate?\"",
  ],
  LIGHT_BG,
  STEEL
));
children.push(spacer(100));

// STAGE 4
children.push(h2("STAGE 4 — REFRAME  (5–10 min)", NAVY));
children.push(body("Purpose: Shift their understanding of the problem without solving it yet. Show them it is not the problem they thought it was."));
children.push(spacer(80));
children.push(calloutBox("Reframe Script",
  [
    "\"Most brands in your position think the problem is awareness and education — that if people just understood the science better, conversion would follow. And for some of your market, that's true. But what the data is actually showing is that the bigger risk isn't that people don't believe the science. It's that the people who believe it most are the ones who are most likely to stretch their budget to buy into the identity it represents — and when they can't sustain that, they don't quietly churn. They become your loudest critics, because they have the most to prove about why they had to stop. That's a different problem. And it's much more preventable than a viral thread.\"",
  ],
  WARN_BG,
  GOLD
));
children.push(spacer(100));

// STAGE 5
children.push(h2("STAGE 5 — FRAMEWORK  (5–10 min)", NAVY));
children.push(body("Purpose: Present a 3-step path in plain language. Not a proposal. A map. Make them feel the path before asking them to walk it."));
children.push(spacer(80));

children.push(threeColTable([
  ["STEP", "WHAT WE DO", "WHAT CHANGES"],
  ["1. Reground the Creative", "Shift the visual and copy language from aspirational deskscapes to consequence documentation — before/after performance proof, real data, real people who look like the actual buyer not the aspirational buyer", "The skeptical 26-33 cohort stops dismissing the brand as 'theater' and starts considering trial. Estimated +25% conversion in that segment."],
  ["2. Rewrite the Retention Narrative", "Replace the Streak loss-aversion mechanic with an Evidence Vault framework — positioning consistent use as self-experimentation, not a performance obligation. Includes explicit permission to stop if it doesn't work.", "-40% 30-day churn. +35% word-of-mouth from users who feel respected rather than managed. Converts the most volatile segment from detractors to advocates."],
  ["3. Localise the Message", "Develop parallel need-state messaging for Surabaya / Bandung / Medan / Semarang — repositioning the product around relationship-building and social sharpness, not Jakarta startup burnout. Geo-targeted digital creative with city-specific copy.", "+20% penetration in non-Jakarta metros currently alienated by Jakarta-centric imagery. Turns 40% of your addressable market from observers into prospects."],
], 1800, 3800, 3760, NAVY));
children.push(spacer(100));

// STAGE 6
children.push(h2("STAGE 6 — CTA  (5 min)", NAVY));
children.push(body("Match the CTA to their openness signal from Stages 2 and 3. Use the lowest appropriate friction level first."));
children.push(spacer(80));
children.push(threeColTable([
  ["SIGNAL IN ROOM", "CTA", "EXACT LANGUAGE"],
  ["Defensive / guarded (short answers, deflecting)", "LOW FRICTION — Diagnostic", "\"Let us put together a quick read on where the current creative is most at risk, no cost, no commitment. You keep what's useful and we go from there.\""],
  ["Open but cautious (engaged, asking questions)", "MED FRICTION — Sprint Proposal", "\"We'd like to come back with a two-week sprint proposal specifically around the retention architecture — the piece that determines whether your early adopters become advocates or detractors.\""],
  ["Fully open (leaning in, asking 'what would you do?')", "HIGH FRICTION — Full Scope", "\"There's a full engagement here across creative, retention strategy, and regional rollout. Can we schedule a working session to scope it properly — bring the right people, build it from the ground up?\""],
], 2400, 2600, 4360, NAVY));

children.push(pageBreak());

// ═══════════════════════════════════════════════════
// SECTION 3: SIGNAL READING GUIDE
// ═══════════════════════════════════════════════════
children.push(sectionDivider("SECTION 3  —  SIGNAL READING GUIDE"));
children.push(body("Train yourself to read the room in real time. These signals override the script.", { italic: true, color: MID }));
children.push(spacer(80));

children.push(twoColTable([
  ["OPEN SIGNALS — proceed deeper", "CLOSE SIGNALS — back off, redirect"],
  ["They answer a question with another question", "Answers become shorter and more clipped"],
  ["They reference a specific person or event with visible emotion", "\"We actually have that handled\" or similar deflection"],
  ["They say \"honestly\" or \"between us\" before an answer", "Checking phone, watch, or glancing at the door"],
  ["Body language shifts: lean in, sustained eye contact", "\"That's a sensitive area for us right now\""],
  ["They interrupt to add detail or correct a nuance", "They redirect to an absent colleague who 'would know better'"],
  ["They ask \"what would you do?\" — this is the green light", "The question gets answered with a question about process"],
], 4680, 4680, STEEL));

children.push(spacer(200));
children.push(h3("BACK-OUT SCRIPTS"));
children.push(body("Use these the moment you detect a close signal. Do not push through a close signal."));
children.push(spacer(80));
children.push(bullet2([new TextRun({ text: "B1 — Soft redirect: ", bold: true, font: BODY_FONT, size: 20, color: NAVY }), new TextRun({ text: "\"Got it — we don't need to go there today. Let me ask you something different...\"", font: BODY_FONT, size: 20, italic: true, color: DARK })]));
children.push(bullet2([new TextRun({ text: "B2 — Park and pivot: ", bold: true, font: BODY_FONT, size: 20, color: NAVY }), new TextRun({ text: "\"Fair enough. Let's park that. What I'm more curious about is...\"", font: BODY_FONT, size: 20, italic: true, color: DARK })]));
children.push(bullet2([new TextRun({ text: "B3 — Show don't ask: ", bold: true, font: BODY_FONT, size: 20, color: NAVY }), new TextRun({ text: "\"Actually, what might be more useful is if I just showed you what we've seen work in similar situations. Would that be helpful?\"", font: BODY_FONT, size: 20, italic: true, color: DARK })]));
children.push(bullet2([new TextRun({ text: "B4 — Hard stop: ", bold: true, font: BODY_FONT, size: 20, color: NAVY }), new TextRun({ text: "\"I appreciate your candor. Let me just focus on what we can actually move forward on together...\"", font: BODY_FONT, size: 20, italic: true, color: DARK })]));

children.push(pageBreak());

// ═══════════════════════════════════════════════════
// SECTION 4: PLAIN LANGUAGE TRANSLATION GUIDE
// ═══════════════════════════════════════════════════
children.push(sectionDivider("SECTION 4  —  PLAIN LANGUAGE TRANSLATION"));
children.push(body("These are the three most important PANTHEON insights. Written so a business owner with no marketing background absorbs them in 30 seconds.", { italic: true, color: MID }));
children.push(spacer(80));

// Insight 1
children.push(h3("INSIGHT 1"));
children.push(new Table({
  width: { size: CONTENT_W, type: WidthType.DXA },
  columnWidths: [1800, 7560],
  rows: [
    new TableRow({ children: [
      new TableCell({ borders: cellBorder(RULE), width: { size: 1800, type: WidthType.DXA }, shading: { fill: NAVY, type: ShadingType.CLEAR }, margins: { top: 100, bottom: 100, left: 160, right: 160 }, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ children: [new TextRun({ text: "PROFESSIONAL", font: HEAD_FONT, size: 18, bold: true, color: "FFFFFF" })] })] }),
      new TableCell({ borders: cellBorder(RULE), width: { size: 7560, type: WidthType.DXA }, shading: { fill: LIGHT_BG, type: ShadingType.CLEAR }, margins: { top: 100, bottom: 100, left: 160, right: 160 }, children: [new Paragraph({ children: [new TextRun({ text: "The primary receptive segment is the status-anxious striver using premium wellness products as proof of upward professional trajectory. The JTBD is not 'beat the 3 PM slump' — it is 'prove to myself and others that I am the type of person who deserves success.'", font: BODY_FONT, size: 20, color: DARK })] })] })
    ]}),
    new TableRow({ children: [
      new TableCell({ borders: cellBorder(RULE), width: { size: 1800, type: WidthType.DXA }, shading: { fill: STEEL, type: ShadingType.CLEAR }, margins: { top: 100, bottom: 100, left: 160, right: 160 }, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ children: [new TextRun({ text: "PLAIN", font: HEAD_FONT, size: 18, bold: true, color: "FFFFFF" })] })] }),
      new TableCell({ borders: cellBorder(RULE), width: { size: 7560, type: WidthType.DXA }, shading: { fill: "FFFFFF", type: ShadingType.CLEAR }, margins: { top: 100, bottom: 100, left: 160, right: 160 }, children: [new Paragraph({ children: [new TextRun({ text: "People are not buying Boost because they need more energy. They are buying it because being seen with Boost says something about them. The juice is a prop in a story they are telling about themselves.", font: BODY_FONT, size: 20, color: DARK })] })] })
    ]}),
    new TableRow({ children: [
      new TableCell({ borders: cellBorder(RULE), width: { size: 1800, type: WidthType.DXA }, shading: { fill: GOLD, type: ShadingType.CLEAR }, margins: { top: 100, bottom: 100, left: 160, right: 160 }, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ children: [new TextRun({ text: "ANALOGY", font: HEAD_FONT, size: 18, bold: true, color: "FFFFFF" })] })] }),
      new TableCell({ borders: cellBorder(RULE), width: { size: 7560, type: WidthType.DXA }, shading: { fill: WARN_BG, type: ShadingType.CLEAR }, margins: { top: 100, bottom: 100, left: 160, right: 160 }, children: [new Paragraph({ children: [new TextRun({ text: "Think of the 24-year-old who buys the Moleskine notebook even though she types everything. It is not about the notebook. It is about being the kind of person who has a Moleskine on their desk.", font: BODY_FONT, size: 20, italic: true, color: DARK })] })] })
    ]}),
  ]
}));
children.push(spacer(120));

// Insight 2
children.push(h3("INSIGHT 2"));
children.push(new Table({
  width: { size: CONTENT_W, type: WidthType.DXA },
  columnWidths: [1800, 7560],
  rows: [
    new TableRow({ children: [
      new TableCell({ borders: cellBorder(RULE), width: { size: 1800, type: WidthType.DXA }, shading: { fill: NAVY, type: ShadingType.CLEAR }, margins: { top: 100, bottom: 100, left: 160, right: 160 }, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ children: [new TextRun({ text: "PROFESSIONAL", font: HEAD_FONT, size: 18, bold: true, color: "FFFFFF" })] })] }),
      new TableCell({ borders: cellBorder(RULE), width: { size: 7560, type: WidthType.DXA }, shading: { fill: LIGHT_BG, type: ShadingType.CLEAR }, margins: { top: 100, bottom: 100, left: 160, right: 160 }, children: [new Paragraph({ children: [new TextRun({ text: "Loss-aversion gamification mechanics (streak-based retention) trigger pre-existing shame spirals in the financially-stretched aspiring-professional cohort, converting early adopters into high-velocity detractors upon purchase discontinuation.", font: BODY_FONT, size: 20, color: DARK })] })] })
    ]}),
    new TableRow({ children: [
      new TableCell({ borders: cellBorder(RULE), width: { size: 1800, type: WidthType.DXA }, shading: { fill: STEEL, type: ShadingType.CLEAR }, margins: { top: 100, bottom: 100, left: 160, right: 160 }, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ children: [new TextRun({ text: "PLAIN", font: HEAD_FONT, size: 18, bold: true, color: "FFFFFF" })] })] }),
      new TableCell({ borders: cellBorder(RULE), width: { size: 7560, type: WidthType.DXA }, shading: { fill: "FFFFFF", type: ShadingType.CLEAR }, margins: { top: 100, bottom: 100, left: 160, right: 160 }, children: [new Paragraph({ children: [new TextRun({ text: "The streak feature is designed to keep people buying. But for the customer who cannot afford to keep buying every day, breaking the streak does not just mean losing a game — it feels like failing at being the person they were trying to become. And people who feel set up to fail tend to get very vocal about who set them up.", font: BODY_FONT, size: 20, color: DARK })] })] })
    ]}),
    new TableRow({ children: [
      new TableCell({ borders: cellBorder(RULE), width: { size: 1800, type: WidthType.DXA }, shading: { fill: GOLD, type: ShadingType.CLEAR }, margins: { top: 100, bottom: 100, left: 160, right: 160 }, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ children: [new TextRun({ text: "ANALOGY", font: HEAD_FONT, size: 18, bold: true, color: "FFFFFF" })] })] }),
      new TableCell({ borders: cellBorder(RULE), width: { size: 7560, type: WidthType.DXA }, shading: { fill: WARN_BG, type: ShadingType.CLEAR }, margins: { top: 100, bottom: 100, left: 160, right: 160 }, children: [new Paragraph({ children: [new TextRun({ text: "Imagine a gym that automatically sends you a message every day you miss a workout: 'Your streak is broken.' For people who can afford the gym and have the time, that is a nudge. For people who are already struggling, it is a reminder that they are failing. They cancel. Then they leave a one-star review.", font: BODY_FONT, size: 20, italic: true, color: DARK })] })] })
    ]}),
  ]
}));
children.push(spacer(120));

// Insight 3
children.push(h3("INSIGHT 3"));
children.push(new Table({
  width: { size: CONTENT_W, type: WidthType.DXA },
  columnWidths: [1800, 7560],
  rows: [
    new TableRow({ children: [
      new TableCell({ borders: cellBorder(RULE), width: { size: 1800, type: WidthType.DXA }, shading: { fill: NAVY, type: ShadingType.CLEAR }, margins: { top: 100, bottom: 100, left: 160, right: 160 }, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ children: [new TextRun({ text: "PROFESSIONAL", font: HEAD_FONT, size: 18, bold: true, color: "FFFFFF" })] })] }),
      new TableCell({ borders: cellBorder(RULE), width: { size: 7560, type: WidthType.DXA }, shading: { fill: LIGHT_BG, type: ShadingType.CLEAR }, margins: { top: 100, bottom: 100, left: 160, right: 160 }, children: [new Paragraph({ children: [new TextRun({ text: "Jakarta-centric creative framing (startup burnout, back-to-back video calls, 3 PM cognitive slump) reads as geographically exclusionary to non-Jakarta metropolitan professionals whose need-states are relationship-oriented rather than task-survival-oriented.", font: BODY_FONT, size: 20, color: DARK })] })] })
    ]}),
    new TableRow({ children: [
      new TableCell({ borders: cellBorder(RULE), width: { size: 1800, type: WidthType.DXA }, shading: { fill: STEEL, type: ShadingType.CLEAR }, margins: { top: 100, bottom: 100, left: 160, right: 160 }, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ children: [new TextRun({ text: "PLAIN", font: HEAD_FONT, size: 18, bold: true, color: "FFFFFF" })] })] }),
      new TableCell({ borders: cellBorder(RULE), width: { size: 7560, type: WidthType.DXA }, shading: { fill: "FFFFFF", type: ShadingType.CLEAR }, margins: { top: 100, bottom: 100, left: 160, right: 160 }, children: [new Paragraph({ children: [new TextRun({ text: "The campaign talks to someone drowning in back-to-back meetings. That is Jakarta. In Surabaya, Semarang, Bandung, or Medan, professionals are not in survival mode — they are in relationship mode. The person they need to show up for is a business contact at a dinner, not an investor on a Zoom call. The product is relevant. The message is not.", font: BODY_FONT, size: 20, color: DARK })] })] })
    ]}),
    new TableRow({ children: [
      new TableCell({ borders: cellBorder(RULE), width: { size: 1800, type: WidthType.DXA }, shading: { fill: GOLD, type: ShadingType.CLEAR }, margins: { top: 100, bottom: 100, left: 160, right: 160 }, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ children: [new TextRun({ text: "ANALOGY", font: HEAD_FONT, size: 18, bold: true, color: "FFFFFF" })] })] }),
      new TableCell({ borders: cellBorder(RULE), width: { size: 7560, type: WidthType.DXA }, shading: { fill: WARN_BG, type: ShadingType.CLEAR }, margins: { top: 100, bottom: 100, left: 160, right: 160 }, children: [new Paragraph({ children: [new TextRun({ text: "If you sell running shoes with an ad that says 'built for New York City traffic,' that ad does nothing for someone who runs on mountain trails. The shoe still fits. The message still does not.", font: BODY_FONT, size: 20, italic: true, color: DARK })] })] })
    ]}),
  ]
}));

children.push(pageBreak());

// ═══════════════════════════════════════════════════
// SECTION 5: STORYTELLERS CTA & SERVICE FIT
// ═══════════════════════════════════════════════════
children.push(sectionDivider("SECTION 5  —  STORYTELLERS SERVICE FIT"));
children.push(body("Only services that have cleared the sanity check are presented here. Do not pitch anything in the [✗ OUT OF SCOPE] list.", { italic: true, color: MID }));
children.push(spacer(80));

// Service 1
children.push(h3("SERVICE 1 — CAMPAIGN REPOSITIONING + CREATIVE DIRECTION"));
children.push(new Table({
  width: { size: CONTENT_W, type: WidthType.DXA },
  columnWidths: [2600, 6760],
  rows: [
    new TableRow({ children: [new TableCell({ borders: cellBorder(RULE), width: {size:2600,type:WidthType.DXA}, shading:{fill:NAVY,type:ShadingType.CLEAR}, margins:{top:80,bottom:80,left:160,right:160}, children:[new Paragraph({children:[new TextRun({text:"SCOPE", font:BODY_FONT, size:20, bold:true, color:"FFFFFF"})]})] }), new TableCell({ borders: cellBorder(RULE), width: {size:6760,type:WidthType.DXA}, shading:{fill:LIGHT_BG,type:ShadingType.CLEAR}, margins:{top:80,bottom:80,left:160,right:160}, children:[new Paragraph({children:[new TextRun({text:"[✓ IN SCOPE]", font:BODY_FONT, size:20, bold:true, color:"2E7D32"})]})] })] }),
    new TableRow({ children: [new TableCell({ borders: cellBorder(RULE), width: {size:2600,type:WidthType.DXA}, shading:{fill:LIGHT_BG,type:ShadingType.CLEAR}, margins:{top:80,bottom:80,left:160,right:160}, children:[new Paragraph({children:[new TextRun({text:"Problem it solves", font:BODY_FONT, size:20, bold:true, color:NAVY})] })] }), new TableCell({ borders: cellBorder(RULE), width: {size:6760,type:WidthType.DXA}, shading:{fill:"FFFFFF",type:ShadingType.CLEAR}, margins:{top:80,bottom:80,left:160,right:160}, children:[new Paragraph({children:[new TextRun({text:"50% of target market currently identifies the deskscape aesthetic as 'exclusionary theater.' The creative is converting skeptics into non-buyers instead of non-buyers into skeptics-worth-converting.", font:BODY_FONT, size:20, color:DARK})] })] })] }),
    new TableRow({ children: [new TableCell({ borders: cellBorder(RULE), width: {size:2600,type:WidthType.DXA}, shading:{fill:LIGHT_BG,type:ShadingType.CLEAR}, margins:{top:80,bottom:80,left:160,right:160}, children:[new Paragraph({children:[new TextRun({text:"How to introduce it", font:BODY_FONT, size:20, bold:true, color:NAVY})] })] }), new TableCell({ borders: cellBorder(RULE), width: {size:6760,type:WidthType.DXA}, shading:{fill:"FFFFFF",type:ShadingType.CLEAR}, margins:{top:80,bottom:80,left:160,right:160}, children:[new Paragraph({children:[new TextRun({text:"\"The science you've built into this product is doing a lot of heavy lifting — but the imagery is asking people to aspire to a life rather than solve a problem. There's a version of this campaign that does both. We'd like to show you what consequence-based creative looks like in your category.\"", font:BODY_FONT, size:20, italic:true, color:DARK})] })] })] }),
    new TableRow({ children: [new TableCell({ borders: cellBorder(RULE), width: {size:2600,type:WidthType.DXA}, shading:{fill:LIGHT_BG,type:ShadingType.CLEAR}, margins:{top:80,bottom:80,left:160,right:160}, children:[new Paragraph({children:[new TextRun({text:"What we're not", font:BODY_FONT, size:20, bold:true, color:NAVY})] })] }), new TableCell({ borders: cellBorder(RULE), width: {size:6760,type:WidthType.DXA}, shading:{fill:"FFFFFF",type:ShadingType.CLEAR}, margins:{top:80,bottom:80,left:160,right:160}, children:[new Paragraph({children:[new TextRun({text:"We do not conduct clinical trials or produce biomarker data. The proof-points must come from Boost's own testing or partner labs — we build the narrative architecture around them.", font:BODY_FONT, size:20, color:DARK})] })] })] }),
  ]
}));
children.push(spacer(160));

// Service 2
children.push(h3("SERVICE 2 — RETENTION MESSAGING + CRM NARRATIVE STRATEGY"));
children.push(new Table({
  width: { size: CONTENT_W, type: WidthType.DXA },
  columnWidths: [2600, 6760],
  rows: [
    new TableRow({ children: [new TableCell({ borders: cellBorder(RULE), width: {size:2600,type:WidthType.DXA}, shading:{fill:NAVY,type:ShadingType.CLEAR}, margins:{top:80,bottom:80,left:160,right:160}, children:[new Paragraph({children:[new TextRun({text:"SCOPE", font:BODY_FONT, size:20, bold:true, color:"FFFFFF"})]})] }), new TableCell({ borders: cellBorder(RULE), width: {size:6760,type:WidthType.DXA}, shading:{fill:LIGHT_BG,type:ShadingType.CLEAR}, margins:{top:80,bottom:80,left:160,right:160}, children:[new Paragraph({children:[new TextRun({text:"[~ ADJACENT] — Storytellers owns the messaging architecture and user journey narrative. App development is client-side.", font:BODY_FONT, size:20, bold:true, color:"D4700A"})]})] })] }),
    new TableRow({ children: [new TableCell({ borders: cellBorder(RULE), width: {size:2600,type:WidthType.DXA}, shading:{fill:LIGHT_BG,type:ShadingType.CLEAR}, margins:{top:80,bottom:80,left:160,right:160}, children:[new Paragraph({children:[new TextRun({text:"Problem it solves", font:BODY_FONT, size:20, bold:true, color:NAVY})] })] }), new TableCell({ borders: cellBorder(RULE), width: {size:6760,type:WidthType.DXA}, shading:{fill:"FFFFFF",type:ShadingType.CLEAR}, margins:{top:80,bottom:80,left:160,right:160}, children:[new Paragraph({children:[new TextRun({text:"The Boost Streak is currently a shame engine. It is driving 30-day churn among the most financially-stretched (and most vocal on social media) segment of the buyer base.", font:BODY_FONT, size:20, color:DARK})] })] })] }),
    new TableRow({ children: [new TableCell({ borders: cellBorder(RULE), width: {size:2600,type:WidthType.DXA}, shading:{fill:LIGHT_BG,type:ShadingType.CLEAR}, margins:{top:80,bottom:80,left:160,right:160}, children:[new Paragraph({children:[new TextRun({text:"How to introduce it", font:BODY_FONT, size:20, bold:true, color:NAVY})] })] }), new TableCell({ borders: cellBorder(RULE), width: {size:6760,type:WidthType.DXA}, shading:{fill:"FFFFFF",type:ShadingType.CLEAR}, margins:{top:80,bottom:80,left:160,right:160}, children:[new Paragraph({children:[new TextRun({text:"\"The retention narrative — how you talk to someone who's been a customer for 30 days — is as important as the acquisition campaign. Right now, the Streak is doing the opposite of what you need. We can redesign what that conversation sounds like, and build the copy and UX language brief your tech team needs to build it properly.\"", font:BODY_FONT, size:20, italic:true, color:DARK})] })] })] }),
    new TableRow({ children: [new TableCell({ borders: cellBorder(RULE), width: {size:2600,type:WidthType.DXA}, shading:{fill:LIGHT_BG,type:ShadingType.CLEAR}, margins:{top:80,bottom:80,left:160,right:160}, children:[new Paragraph({children:[new TextRun({text:"What we're not", font:BODY_FONT, size:20, bold:true, color:NAVY})] })] }), new TableCell({ borders: cellBorder(RULE), width: {size:6760,type:WidthType.DXA}, shading:{fill:"FFFFFF",type:ShadingType.CLEAR}, margins:{top:80,bottom:80,left:160,right:160}, children:[new Paragraph({children:[new TextRun({text:"We do not build apps or databases. We deliver the strategic narrative, the user journey map, the copy system, and the brief for the Evidence Vault. Boost's product/tech team builds it.", font:BODY_FONT, size:20, color:DARK})] })] })] }),
  ]
}));
children.push(spacer(160));

// Service 3
children.push(h3("SERVICE 3 — GO-TO-MARKET STRATEGY, REGIONAL CREATIVE DIRECTION"));
children.push(new Table({
  width: { size: CONTENT_W, type: WidthType.DXA },
  columnWidths: [2600, 6760],
  rows: [
    new TableRow({ children: [new TableCell({ borders: cellBorder(RULE), width: {size:2600,type:WidthType.DXA}, shading:{fill:NAVY,type:ShadingType.CLEAR}, margins:{top:80,bottom:80,left:160,right:160}, children:[new Paragraph({children:[new TextRun({text:"SCOPE", font:BODY_FONT, size:20, bold:true, color:"FFFFFF"})]})] }), new TableCell({ borders: cellBorder(RULE), width: {size:6760,type:WidthType.DXA}, shading:{fill:LIGHT_BG,type:ShadingType.CLEAR}, margins:{top:80,bottom:80,left:160,right:160}, children:[new Paragraph({children:[new TextRun({text:"[✓ IN SCOPE]", font:BODY_FONT, size:20, bold:true, color:"2E7D32"})]})] })] }),
    new TableRow({ children: [new TableCell({ borders: cellBorder(RULE), width: {size:2600,type:WidthType.DXA}, shading:{fill:LIGHT_BG,type:ShadingType.CLEAR}, margins:{top:80,bottom:80,left:160,right:160}, children:[new Paragraph({children:[new TextRun({text:"Problem it solves", font:BODY_FONT, size:20, bold:true, color:NAVY})] })] }), new TableCell({ borders: cellBorder(RULE), width: {size:6760,type:WidthType.DXA}, shading:{fill:"FFFFFF",type:ShadingType.CLEAR}, margins:{top:80,bottom:80,left:160,right:160}, children:[new Paragraph({children:[new TextRun({text:"40% of metropolitan Indonesia is currently reading the campaign as 'designed for someone else.' Surabaya, Bandung, Semarang, Medan have fundamentally different professional need-states that the current creative does not address.", font:BODY_FONT, size:20, color:DARK})] })] })] }),
    new TableRow({ children: [new TableCell({ borders: cellBorder(RULE), width: {size:2600,type:WidthType.DXA}, shading:{fill:LIGHT_BG,type:ShadingType.CLEAR}, margins:{top:80,bottom:80,left:160,right:160}, children:[new Paragraph({children:[new TextRun({text:"How to introduce it", font:BODY_FONT, size:20, bold:true, color:NAVY})] })] }), new TableCell({ borders: cellBorder(RULE), width: {size:6760,type:WidthType.DXA}, shading:{fill:"FFFFFF",type:ShadingType.CLEAR}, margins:{top:80,bottom:80,left:160,right:160}, children:[new Paragraph({children:[new TextRun({text:"\"There's a version of this launch that treats Surabaya and Semarang as extensions of Jakarta. And there's a version that treats them as distinct markets with their own professional culture. The second version costs roughly the same to execute — it just requires different messaging. We can build that.\"", font:BODY_FONT, size:20, italic:true, color:DARK})] })] })] }),
    new TableRow({ children: [new TableCell({ borders: cellBorder(RULE), width: {size:2600,type:WidthType.DXA}, shading:{fill:LIGHT_BG,type:ShadingType.CLEAR}, margins:{top:80,bottom:80,left:160,right:160}, children:[new Paragraph({children:[new TextRun({text:"What we're not", font:BODY_FONT, size:20, bold:true, color:NAVY})] })] }), new TableCell({ borders: cellBorder(RULE), width: {size:6760,type:WidthType.DXA}, shading:{fill:"FFFFFF",type:ShadingType.CLEAR}, margins:{top:80,bottom:80,left:160,right:160}, children:[new Paragraph({children:[new TextRun({text:"We do not manage media buying or regional field operations. We build the strategy and creative briefs; Boost's media team or agency executes the placement.", font:BODY_FONT, size:20, color:DARK})] })] })] }),
  ]
}));
children.push(spacer(200));

// Out of scope
children.push(calloutBox(
  "SERVICES EXCLUDED FROM THIS MEETING",
  [
    "[✗ OUT OF SCOPE] — App / product development: Evidence Vault technical build. Refer to Boost's internal product team or a technology partner. Storytellers' role: deliver the messaging system and UX copy brief.",
    "[✗ OUT OF SCOPE] — Clinical research / biomarker studies. The science is Boost's responsibility. Storytellers builds the narrative around data that Boost already owns or commissions.",
    "[~ ADJACENT, PRESENT CONDITIONALLY] — Revenue/monetization consulting on price tiering. Storytellers can advise on the positioning and messaging of price tiers (dignity framing, accessibility narrative). Final pricing decisions are the client's.",
  ],
  RISK_BG,
  RED
));

children.push(pageBreak());

// ═══════════════════════════════════════════════════
// SECTION 6: MEETING LOGISTICS
// ═══════════════════════════════════════════════════
children.push(sectionDivider("SECTION 6  —  MEETING LOGISTICS"));
children.push(spacer(80));

children.push(twoColTable([
  ["LOGISTICS", "DETAIL"],
  ["Recommended duration", "45–60 minutes. Do not go over 60 unless they are clearly in Stage 6 and moving toward scope."],
  ["Attendees from Storytellers", "Maximum 3. Recommended: Account lead (runs Stages 1-4) + Strategy lead (presents Framework in Stage 5) + Silent third (reads the room, takes notes, watches body language)."],
  ["Materials to bring", "Nothing physical unless specifically requested. This is a conversation, not a pitch. If you must bring something, bring a single printed one-page showing the 3-step framework from Stage 5 — no logos, no branding, no deck."],
  ["Pre-meeting action", "Verify current Boost social media presence and tone. Identify whether any regional campaign activity is already in-market. Check if 'Boost Streak' app is live or still in development — changes the urgency conversation significantly."],
  ["Post-meeting action (within 24 hours)", "Send a one-paragraph email that mirrors back exactly what you heard, names the one thing they seemed most concerned about, and states the agreed next step. No deck. No proposal. Just signal you were listening."],
  ["If they ask for a proposal on the spot", "\"Give us 48 hours — we want to make sure what we put in front of you is actually scoped to what matters to you, not a generic retainer template.\""],
], 2800, 6560, NAVY));

children.push(spacer(200));

children.push(calloutBox(
  "POST-MEETING: LIVE UPDATE INSTRUCTIONS",
  [
    "This document is designed to be updated after the meeting. Add the following at the bottom of Section 2:",
    "WHAT WAS SAID: [key quotes, moments of opening or closing]",
    "SIGNALS DETECTED: [open / close / mixed — and which questions triggered which]",
    "CTA RESPONSE: [which CTA was offered, how they responded, exact language they used]",
    "AGREED NEXT STEP: [what was confirmed, by whom, by when]",
    "WHAT TO SEND: [content of follow-up email within 24 hours]",
  ],
  LIGHT_BG,
  STEEL
));

children.push(spacer(200));
children.push(rule());
children.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { before: 160, after: 80 },
  children: [new TextRun({ text: "STORYTELLERS STRATEGIC ADVISORY  —  INTERNAL DOCUMENT", font: HEAD_FONT, size: 18, bold: true, color: NAVY, allCaps: true })]
}));
children.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { before: 0, after: 60 },
  children: [new TextRun({ text: "Intelligence sourced from PANTHEON Synthesis Intelligence  |  Classification: Internal Only  |  6 March 2026", font: BODY_FONT, size: 18, italic: true, color: MID })]
}));

// ═══════════════════════════════════════════════════
// ASSEMBLE DOCUMENT
// ═══════════════════════════════════════════════════
const doc = new Document({
  numbering: {
    config: [
      {
        reference: "bullets",
        levels: [{
          level: 0, format: LevelFormat.BULLET, text: "\u2022",
          alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 540, hanging: 280 } } }
        }]
      },
      {
        reference: "sub-bullets",
        levels: [{
          level: 0, format: LevelFormat.BULLET, text: "\u25E6",
          alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 900, hanging: 280 } } }
        }]
      },
      {
        reference: "numbers",
        levels: [{
          level: 0, format: LevelFormat.DECIMAL, text: "%1.",
          alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 540, hanging: 280 } } }
        }]
      },
    ]
  },
  styles: {
    default: {
      document: { run: { font: BODY_FONT, size: 20, color: DARK } }
    },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: HEAD_FONT, color: NAVY },
        paragraph: { spacing: { before: 360, after: 120 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, font: HEAD_FONT, color: STEEL },
        paragraph: { spacing: { before: 280, after: 100 }, outlineLevel: 1 } },
    ]
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
      }
    },
    headers: {
      default: new Header({
        children: [new Paragraph({
          border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: GOLD, space: 1 } },
          children: [
            new TextRun({ text: "STORYTELLERS  |  CLIENT MEETING PREP — BOOST  |  INTERNAL ONLY", font: BODY_FONT, size: 16, color: MID }),
          ]
        })]
      })
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          border: { top: { style: BorderStyle.SINGLE, size: 4, color: GOLD, space: 1 } },
          children: [
            new TextRun({ text: "CONFIDENTIAL — Internal Distribution Only  |  Page ", font: BODY_FONT, size: 16, color: MID }),
            new TextRun({ children: [PageNumber.CURRENT], font: BODY_FONT, size: 16, color: MID }),
            new TextRun({ text: " of ", font: BODY_FONT, size: 16, color: MID }),
            new TextRun({ children: [PageNumber.TOTAL_PAGES], font: BODY_FONT, size: 16, color: MID }),
          ]
        })]
      })
    },
    children
  }]
});

const OUTPUT = "C:\\Users\\johns\\Documents\\Antigravity\\pantheon-app\\reports\\Boost_MeetingPrep_20260306.docx";
Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync(OUTPUT, buffer);
  console.log("SUCCESS: " + OUTPUT);
}).catch(err => {
  console.error("ERROR:", err);
  process.exit(1);
});
