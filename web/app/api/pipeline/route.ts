import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const maxDuration = 300;

const MODAL_URL =
  process.env.MODAL_API_URL ||
  "https://leonardijohnson0--pantheon-engine-fastapi-app.modal.run";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();

    const upstream = await fetch(`${MODAL_URL}/run_pipeline`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      // @ts-ignore — Node 18+ fetch supports signal
      signal: AbortSignal.timeout(25_000),
    });

    const text = await upstream.text();

    let data: unknown;
    try {
      data = JSON.parse(text);
    } catch {
      return NextResponse.json(
        { error: `Modal returned non-JSON (${upstream.status}): ${text.slice(0, 500)}` },
        { status: upstream.status }
      );
    }

    if (!upstream.ok) {
      return NextResponse.json(
        { error: (data as Record<string, string>)?.error || `Upstream ${upstream.status}` },
        { status: upstream.status }
      );
    }

    return NextResponse.json(data);
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : "Proxy error";
    console.error("[pipeline proxy]", msg);
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}
