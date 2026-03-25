import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const maxDuration = 120;

const MODAL_URL =
  process.env.MODAL_API_URL ||
  "https://leonardijohnson0--pantheon-engine-fastapi-app.modal.run";

export async function POST(req: NextRequest) {
  try {
    const formData = await req.formData();
    const file = formData.get("file") as File | null;
    if (!file) {
      return NextResponse.json({ error: "No file provided" }, { status: 400 });
    }

    // Forward the multipart form directly to Modal's /extract-brief endpoint
    const upstream = await fetch(`${MODAL_URL}/extract-brief`, {
      method: "POST",
      body: formData,
      signal: AbortSignal.timeout(115_000),
    });

    const text = await upstream.text();
    let data: unknown;
    try {
      data = JSON.parse(text);
    } catch {
      return NextResponse.json(
        { error: `Modal error (${upstream.status}): ${text.slice(0, 300)}`, text: "", images: [], slide_count: 0 },
        { status: upstream.status || 500 }
      );
    }
    return NextResponse.json(data, { status: upstream.status });
  } catch (err: unknown) {
    console.error("[extract-visual]", err);
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "Extraction failed", text: "", images: [], slide_count: 0 },
      { status: 500 }
    );
  }
}
