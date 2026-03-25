/**
 * ════════════════════════════════════════════════════════════════
 * HUMAN WHISPERER — /api/human-whisperer
 * ════════════════════════════════════════════════════════════════
 *
 * PURPOSE:  Individual person intelligence for 1-on-1 sales conversations.
 *
 * INPUT:    linkedin_url + instagram_url + product_details
 *           (scraped social profiles of a SPECIFIC NAMED PERSON)
 *
 * OUTPUT:   Structured genome + conversation prep for talking TO that individual
 *           - Personality genome (Big Five + behavioral traits)
 *           - Life blueprint simulation
 *           - Section 0: Quick Brief (HOOK / STAY / CLOSE)
 *           - Section 1: Human Snapshot
 *           - Section 2: Conversation Architecture (1-on-1)
 *           - Section 3: Signal Reading Guide
 *           - Section 5: Product Fit & CTA
 *
 * NOT FOR:  B2B brand meetings. PANTHEON research reports.
 *           If you have a PANTHEON report and a brand company — use /api/download/client-whisperer
 *
 * BACKEND:  Proxies to Modal pipeline (scrapers.py → vision.py → engine.py → strategy.py)
 *           Full pipeline takes ~2–4 minutes (LinkedIn scrape + Instagram scrape + genome build)
 * ════════════════════════════════════════════════════════════════
 */

import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const maxDuration = 300; // 5 min — scraping + genome pipeline is long

const HUMAN_WHISPERER_URL =
  process.env.WHISPER_API_URL ||
  "https://leonardijohnson0--client-whisperer-fastapi-app.modal.run";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();

    // Validate that this is an individual-profile request
    if (!body.linkedin_url && !body.instagram_url) {
      return NextResponse.json(
        { error: "Human Whisperer requires linkedin_url and/or instagram_url of an individual person. For PANTHEON brand reports use /api/download/client-whisperer instead." },
        { status: 400 }
      );
    }

    const upstream = await fetch(`${HUMAN_WHISPERER_URL}/whisper`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      // @ts-ignore — Node 18+ supports signal on fetch
      signal: AbortSignal.timeout(280_000),
    });

    const data = await upstream.json();

    if (!upstream.ok) {
      return NextResponse.json(
        { error: data.detail || `Upstream error ${upstream.status}` },
        { status: upstream.status }
      );
    }

    return NextResponse.json(data);
  } catch (err: unknown) {
    console.error("[human-whisperer proxy]", err);
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "Proxy error" },
      { status: 500 }
    );
  }
}
