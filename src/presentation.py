import os
import json
import time
import subprocess
from datetime import datetime
from pathlib import Path

_DECK_CONTENT_TOOL = {
    "name": "extract_deck_content",
    "description": "Extract structured slide deck content from the PANTHEON research report.",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Report title (≤12 words)"},
            "brief_synopsis": {"type": "string", "description": "One sentence campaign/product summary"},
            "executive_summary": {
                "type": "object",
                "properties": {
                    "headline": {"type": "string", "description": "The Headline Truth — one sentence"},
                    "findings": {
                        "type": "array",
                        "items": {"type": "string", "description": "Key finding (1-2 sentences, specific)"},
                        "minItems": 3,
                        "maxItems": 5,
                    },
                },
                "required": ["headline", "findings"],
            },
            "market_context": {
                "type": "object",
                "properties": {
                    "headline": {"type": "string", "description": "Market context headline (≤10 words)"},
                    "stats": {
                        "type": "array",
                        "items": {"type": "string", "description": "Key stat or data point (≤15 words)"},
                        "minItems": 2,
                        "maxItems": 3,
                    },
                    "paragraph": {"type": "string", "description": "2-3 sentence market context paragraph"},
                },
                "required": ["headline", "stats", "paragraph"],
            },
            "audience_insights": {
                "type": "object",
                "properties": {
                    "headline": {"type": "string", "description": "Audience insight headline (≤10 words)"},
                    "archetypes": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string", "description": "Archetype name (≤5 words)"},
                                "age_range": {"type": "string", "description": "Age range e.g. '26-32'"},
                                "profile": {"type": "string", "description": "3-4 sentence psychographic profile"},
                            },
                            "required": ["name", "age_range", "profile"],
                        },
                        "minItems": 2,
                        "maxItems": 3,
                    },
                },
                "required": ["headline", "archetypes"],
            },
            "consumer_response": {
                "type": "object",
                "properties": {
                    "headline": {"type": "string"},
                    "findings": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "metric": {"type": "string", "description": "Short label (≤6 words)"},
                                "value": {"type": "string", "description": "Key metric value e.g. '72%' or 'High'"},
                                "detail": {"type": "string", "description": "One sentence explanation"},
                            },
                            "required": ["metric", "value", "detail"],
                        },
                        "minItems": 2,
                        "maxItems": 4,
                    },
                },
                "required": ["headline", "findings"],
            },
            "key_insights": {
                "type": "object",
                "properties": {
                    "headline": {"type": "string"},
                    "insights": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string", "description": "Insight title (≤8 words)"},
                                "body": {"type": "string", "description": "1-2 sentence explanation"},
                            },
                            "required": ["title", "body"],
                        },
                        "minItems": 2,
                        "maxItems": 4,
                    },
                },
                "required": ["headline", "insights"],
            },
            "recommendations": {
                "type": "object",
                "properties": {
                    "headline": {"type": "string"},
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "priority": {"type": "string", "enum": ["High", "Medium", "Low"]},
                                "title": {"type": "string", "description": "Recommendation title (≤8 words)"},
                                "action": {"type": "string", "description": "One sentence action item"},
                            },
                            "required": ["priority", "title", "action"],
                        },
                        "minItems": 2,
                        "maxItems": 4,
                    },
                },
                "required": ["headline", "items"],
            },
            "risks": {
                "type": "object",
                "properties": {
                    "headline": {"type": "string"},
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "level": {"type": "string", "enum": ["High", "Medium", "Low"]},
                                "title": {"type": "string", "description": "Risk title (≤8 words)"},
                                "indicator": {"type": "string", "description": "One sentence kill switch signal"},
                            },
                            "required": ["level", "title", "indicator"],
                        },
                        "minItems": 2,
                        "maxItems": 4,
                    },
                },
                "required": ["headline", "items"],
            },
        },
        "required": [
            "title", "brief_synopsis",
            "executive_summary", "market_context", "audience_insights",
            "consumer_response", "key_insights", "recommendations", "risks",
        ],
    },
}

_PPTXGENJS_TEMPLATE = r"""
const pptxgen = require('D:/npm-global/node_modules/pptxgenjs');
const fs = require('fs');

const data = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const outFile = process.argv[3];

const NAVY="1E2761", DARK="0D1B2A", ICE="CADCFC", GOLD="E8B04B";
const WHITE="F7F9FC", MUTED="8896A8", BODY="334155";

let pres = new pptxgen();
pres.layout = 'LAYOUT_16x9';
pres.author = 'PANTHEON';
pres.title = data.title;

function hdr(slide, title) {
    slide.addShape(pres.shapes.RECTANGLE, {x:0,y:0,w:10,h:0.72,fill:{color:NAVY},line:{color:NAVY}});
    slide.addShape(pres.shapes.RECTANGLE, {x:0,y:0,w:0.2,h:5.625,fill:{color:GOLD},line:{color:GOLD}});
    slide.addText(title, {x:0.4,y:0.1,w:9.3,h:0.52,fontSize:22,color:WHITE,bold:true,fontFace:"Calibri",valign:"middle",margin:0});
}

// §0 COVER
let s0 = pres.addSlide();
s0.background = {color:DARK};
s0.addShape(pres.shapes.RECTANGLE, {x:0,y:0,w:0.2,h:5.625,fill:{color:GOLD},line:{color:GOLD}});
s0.addText("PANTHEON\u2122", {x:7.0,y:0.22,w:2.8,h:0.38,fontSize:11,color:GOLD,bold:true,align:"right",fontFace:"Calibri"});
s0.addText(data.title, {x:0.45,y:1.0,w:9.3,h:1.55,fontSize:36,color:WHITE,bold:true,fontFace:"Calibri",valign:"middle"});
s0.addShape(pres.shapes.RECTANGLE, {x:0.45,y:2.72,w:2.8,h:0.045,fill:{color:GOLD},line:{color:GOLD}});
s0.addText(data.brief_synopsis, {x:0.45,y:2.87,w:9.2,h:0.78,fontSize:15,color:ICE,italic:true,fontFace:"Calibri",valign:"top"});
s0.addText("Target Demographic: " + data.target, {x:0.45,y:3.78,w:8.5,h:0.35,fontSize:11,color:MUTED});
s0.addText(data.date, {x:7.2,y:5.12,w:2.6,h:0.3,fontSize:10,color:MUTED,align:"right"});
s0.addText("Synthetic Focus Group Research", {x:0.45,y:5.12,w:5,h:0.3,fontSize:10,color:MUTED});

// §1 EXECUTIVE SUMMARY
let s1 = pres.addSlide();
s1.background = {color:WHITE};
hdr(s1, "Executive Summary");
s1.addText(data.executive_summary.headline, {x:0.45,y:0.82,w:9.3,h:0.42,fontSize:15,color:NAVY,bold:true,italic:true,fontFace:"Calibri"});
(data.executive_summary.findings || []).slice(0,5).forEach((f, i) => {
    let y = 1.38 + i * 0.75;
    s1.addShape(pres.shapes.RECTANGLE, {x:0.45,y:y+0.04,w:0.06,h:0.4,fill:{color:GOLD},line:{color:GOLD}});
    s1.addText(f, {x:0.62,y:y,w:9.0,h:0.56,fontSize:13,color:BODY,fontFace:"Calibri",valign:"middle"});
});

// §2 AGENDA
let s2 = pres.addSlide();
s2.background = {color:WHITE};
hdr(s2, "Agenda");
["Market & Demographic Context","Audience Psychology & Deep-Dive","Consumer Response Analysis","Key Insights & Patterns","Strategic Recommendations","Risk Assessment & Kill Switch Signals"].forEach((sec, i) => {
    let y = 0.9 + i * 0.72;
    let nc = i % 2 === 0 ? GOLD : NAVY;
    s2.addShape(pres.shapes.RECTANGLE, {x:0.45,y:y+0.04,w:0.34,h:0.34,fill:{color:nc},line:{color:nc}});
    s2.addText(String(i+1), {x:0.45,y:y+0.04,w:0.34,h:0.34,fontSize:12,color:WHITE,bold:true,align:"center",valign:"middle",margin:0});
    s2.addText(sec, {x:0.92,y:y,w:8.8,h:0.44,fontSize:14,color:BODY,fontFace:"Calibri",valign:"middle"});
});

// §3 MARKET CONTEXT
let s3 = pres.addSlide();
s3.background = {color:WHITE};
hdr(s3, "Market & Demographic Context");
s3.addText(data.market_context.headline, {x:0.45,y:0.82,w:9.3,h:0.4,fontSize:15,color:NAVY,bold:true,italic:true});
(data.market_context.stats || []).slice(0,3).forEach((stat, i) => {
    let x = 0.45 + i * 3.12;
    s3.addShape(pres.shapes.RECTANGLE, {x:x,y:1.35,w:2.92,h:1.38,fill:{color:NAVY},line:{color:NAVY}});
    s3.addText(stat, {x:x+0.1,y:1.38,w:2.72,h:1.32,fontSize:13,color:ICE,fontFace:"Calibri",valign:"middle",align:"center"});
});
s3.addText(data.market_context.paragraph, {x:0.45,y:2.9,w:9.3,h:2.45,fontSize:12,color:BODY,fontFace:"Calibri",valign:"top"});

// §4 AUDIENCE
let s4 = pres.addSlide();
s4.background = {color:WHITE};
hdr(s4, "Audience Psychology & Deep-Dive");
s4.addText(data.audience_insights.headline, {x:0.45,y:0.82,w:9.3,h:0.4,fontSize:15,color:NAVY,bold:true,italic:true});
let archs = (data.audience_insights.archetypes || []).slice(0,3);
let cw = archs.length > 0 ? (9.1 / archs.length) - 0.1 : 9.1;
archs.forEach((arch, i) => {
    let x = 0.45 + i * (cw + 0.1);
    s4.addShape(pres.shapes.RECTANGLE, {x:x,y:1.35,w:cw,h:3.98,fill:{color:"F0F4F8"},line:{color:"E2E8F0"}});
    s4.addShape(pres.shapes.RECTANGLE, {x:x,y:1.35,w:cw,h:0.32,fill:{color:NAVY},line:{color:NAVY}});
    s4.addText(arch.name, {x:x+0.08,y:1.35,w:cw-0.16,h:0.32,fontSize:11,color:WHITE,bold:true,valign:"middle",margin:0});
    s4.addText("Age: " + (arch.age_range || ""), {x:x+0.08,y:1.76,w:cw-0.16,h:0.3,fontSize:10,color:GOLD,bold:true});
    s4.addText(arch.profile || "", {x:x+0.08,y:2.12,w:cw-0.16,h:3.1,fontSize:11,color:BODY,fontFace:"Calibri",valign:"top"});
});

// §5 CONSUMER RESPONSE
let s5 = pres.addSlide();
s5.background = {color:WHITE};
hdr(s5, "Consumer Response Analysis");
s5.addText(data.consumer_response.headline, {x:0.45,y:0.82,w:9.3,h:0.4,fontSize:15,color:NAVY,bold:true,italic:true});
(data.consumer_response.findings || []).slice(0,4).forEach((f, i) => {
    let y = 1.35 + i * 0.97;
    s5.addShape(pres.shapes.RECTANGLE, {x:0.45,y:y,w:9.3,h:0.87,fill:{color:"F8FAFC"},line:{color:"E2E8F0"}});
    s5.addShape(pres.shapes.RECTANGLE, {x:0.45,y:y,w:0.06,h:0.87,fill:{color:GOLD},line:{color:GOLD}});
    s5.addText(f.metric || "", {x:0.62,y:y+0.06,w:1.8,h:0.32,fontSize:10,color:MUTED,bold:true});
    s5.addText(f.value || "", {x:2.55,y:y+0.04,w:1.2,h:0.38,fontSize:18,color:NAVY,bold:true,align:"center"});
    s5.addText(f.detail || "", {x:0.62,y:y+0.44,w:8.9,h:0.36,fontSize:11,color:BODY});
});

// §6 KEY INSIGHTS
let s6 = pres.addSlide();
s6.background = {color:WHITE};
hdr(s6, "Key Insights & Patterns");
s6.addText(data.key_insights.headline, {x:0.45,y:0.82,w:9.3,h:0.4,fontSize:15,color:NAVY,bold:true,italic:true});
(data.key_insights.insights || []).slice(0,4).forEach((ins, i) => {
    let y = 1.35 + i * 0.97;
    s6.addShape(pres.shapes.RECTANGLE, {x:0.45,y:y,w:9.3,h:0.87,fill:{color:"F8FAFC"},line:{color:"E2E8F0"}});
    s6.addShape(pres.shapes.RECTANGLE, {x:0.45,y:y,w:0.06,h:0.87,fill:{color:GOLD},line:{color:GOLD}});
    s6.addText(ins.title || "", {x:0.62,y:y+0.06,w:9.0,h:0.3,fontSize:12,color:NAVY,bold:true});
    s6.addText(ins.body || "", {x:0.62,y:y+0.41,w:9.0,h:0.4,fontSize:11,color:BODY});
});

// §7 RECOMMENDATIONS
let s7 = pres.addSlide();
s7.background = {color:WHITE};
hdr(s7, "Strategic Recommendations");
s7.addText(data.recommendations.headline, {x:0.45,y:0.82,w:9.3,h:0.4,fontSize:15,color:NAVY,bold:true,italic:true});
(data.recommendations.items || []).slice(0,4).forEach((rec, i) => {
    let y = 1.35 + i * 0.97;
    let pc = rec.priority === "High" ? "DC2626" : (rec.priority === "Medium" ? GOLD : "22C55E");
    s7.addShape(pres.shapes.RECTANGLE, {x:0.45,y:y,w:9.3,h:0.87,fill:{color:"F8FAFC"},line:{color:"E2E8F0"}});
    s7.addShape(pres.shapes.RECTANGLE, {x:0.45,y:y,w:0.06,h:0.87,fill:{color:pc},line:{color:pc}});
    s7.addShape(pres.shapes.RECTANGLE, {x:8.52,y:y+0.19,w:0.88,h:0.27,fill:{color:pc},line:{color:pc}});
    s7.addText(rec.priority || "", {x:8.52,y:y+0.19,w:0.88,h:0.27,fontSize:9,color:WHITE,bold:true,align:"center",valign:"middle",margin:0});
    s7.addText(rec.title || "", {x:0.62,y:y+0.06,w:7.7,h:0.3,fontSize:12,color:NAVY,bold:true});
    s7.addText(rec.action || "", {x:0.62,y:y+0.42,w:9.0,h:0.38,fontSize:11,color:BODY});
});

// §8 RISKS
let s8 = pres.addSlide();
s8.background = {color:WHITE};
hdr(s8, "Risk Assessment & Kill Switch Signals");
s8.addText(data.risks.headline, {x:0.45,y:0.82,w:9.3,h:0.4,fontSize:15,color:NAVY,bold:true,italic:true});
(data.risks.items || []).slice(0,4).forEach((r, i) => {
    let y = 1.35 + i * 0.97;
    let rc = r.level === "High" ? "DC2626" : (r.level === "Medium" ? GOLD : "22C55E");
    s8.addShape(pres.shapes.RECTANGLE, {x:0.45,y:y,w:9.3,h:0.87,fill:{color:"F8FAFC"},line:{color:"E2E8F0"}});
    s8.addShape(pres.shapes.RECTANGLE, {x:0.45,y:y,w:0.06,h:0.87,fill:{color:rc},line:{color:rc}});
    s8.addShape(pres.shapes.RECTANGLE, {x:8.52,y:y+0.19,w:0.88,h:0.27,fill:{color:rc},line:{color:rc}});
    s8.addText(r.level || "", {x:8.52,y:y+0.19,w:0.88,h:0.27,fontSize:9,color:WHITE,bold:true,align:"center",valign:"middle",margin:0});
    s8.addText(r.title || "", {x:0.62,y:y+0.06,w:7.7,h:0.3,fontSize:12,color:NAVY,bold:true});
    s8.addText(r.indicator || "", {x:0.62,y:y+0.42,w:9.0,h:0.38,fontSize:11,color:BODY});
});

// §9 CLOSING
let s9 = pres.addSlide();
s9.background = {color:DARK};
s9.addShape(pres.shapes.RECTANGLE, {x:0,y:0,w:0.2,h:5.625,fill:{color:GOLD},line:{color:GOLD}});
s9.addText("PANTHEON\u2122", {x:0.45,y:1.1,w:9.1,h:1.05,fontSize:52,color:WHITE,bold:true,fontFace:"Calibri",align:"center"});
s9.addShape(pres.shapes.RECTANGLE, {x:3.1,y:2.25,w:3.8,h:0.045,fill:{color:GOLD},line:{color:GOLD}});
s9.addText("Synthetic Focus Group Research Engine", {x:0.45,y:2.38,w:9.1,h:0.44,fontSize:14,color:ICE,italic:true,align:"center"});
s9.addText("Powered by Anthropic Claude \u00b7 Modal Serverless \u00b7 Supabase", {x:0.45,y:2.95,w:9.1,h:0.35,fontSize:11,color:MUTED,align:"center"});
s9.addText("This report was generated using synthetic focus group simulation. All respondents are AI-synthesized personas. Results are for strategic guidance only.", {x:1.2,y:4.55,w:7.6,h:0.72,fontSize:9,color:MUTED,align:"center",italic:true});
s9.addText(data.date, {x:7.2,y:5.12,w:2.6,h:0.3,fontSize:10,color:MUTED,align:"right"});

pres.writeFile({fileName: outFile})
    .then(() => { console.log("PPTX_DONE"); process.exit(0); })
    .catch(e => { console.error("PPTX_ERR: " + e.message); process.exit(1); });
"""


def _extract_deck_content(anthropic_client, md_content: str, target: str, brief: str, client: str) -> dict | None:
    import anthropic as _anthropic

    system = (
        "You are an expert MBB (McKinsey/Bain/BCG) presentation strategist. "
        "Extract concise, punchy content from the PANTHEON research report for a "
        "professional executive slide deck. Be specific and data-driven. "
        "Every field must be populated with meaningful content from the report."
    )
    user_msg = (
        f"Extract slide deck content from this PANTHEON Research Intelligence Report.\n\n"
        f"Client/Product context: {client or 'Not specified'}\n"
        f"Target demographic: {target}\n"
        f"Campaign brief: {brief}\n\n"
        f"--- REPORT ---\n{md_content[:12000]}"
    )

    for attempt in range(1, 3):
        try:
            resp = anthropic_client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                system=system,
                tools=[_DECK_CONTENT_TOOL],
                tool_choice={"type": "tool", "name": "extract_deck_content"},
                messages=[{"role": "user", "content": user_msg}],
            )
            block = next((b for b in resp.content if b.type == "tool_use"), None)
            if block is None:
                raise ValueError("No tool_use block returned")
            return block.input
        except _anthropic.RateLimitError:
            print("  Node 6: rate limit hit — sleeping 65s...")
            time.sleep(65)
        except Exception as e:
            print(f"  Node 6: extraction attempt {attempt}/2 failed: {e}")
            if attempt < 2:
                time.sleep(5)
    return None


def _save_presentation(md_path: Path, base_name: str, target: str, brief: str, client: str = "") -> None:
    import anthropic as _anthropic
    from dotenv import load_dotenv
    load_dotenv(md_path.parent.parent / "pantheon.env", override=True)
    ac = _anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    md_content = md_path.read_text(encoding="utf-8")

    deck_data = _extract_deck_content(ac, md_content, target, brief, client)
    if not deck_data:
        print("  Node 6: Failed to extract deck content — skipping PPTX.")
        return

    deck_data.update({"target": target, "date": datetime.now().strftime("%B %Y")})

    out_dir = md_path.parent
    json_path = out_dir / f"{base_name}_deck_data.json"
    js_path = out_dir / f"{base_name}_gen.js"
    pptx_path = out_dir / f"{base_name}.pptx"

    json_path.write_text(json.dumps(deck_data, ensure_ascii=False, indent=2), encoding="utf-8")
    js_path.write_text(_PPTXGENJS_TEMPLATE, encoding="utf-8")

    try:
        result = subprocess.run(
            ["node", str(js_path), str(json_path), str(pptx_path)],
            capture_output=True, text=True, timeout=90, cwd=str(out_dir)
        )
        if result.returncode == 0 and pptx_path.exists():
            print(f"  Deck saved ({pptx_path.stat().st_size // 1024} KB) → {pptx_path}")
            print(f"PANTHEON_PPTX_FILE::{pptx_path.name}")
        else:
            print(f"  Node 6: pptxgenjs failed:\n    {result.stderr[:300]}")
    except subprocess.TimeoutExpired:
        print("  Node 6: Node.js timed out after 90s — skipping presentation.")
    except Exception as e:
        print(f"  Node 6: Execution error: {e}")
    finally:
        for tmp in [json_path, js_path]:
            tmp.unlink(missing_ok=True)
