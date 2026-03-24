import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const maxDuration = 300; // 5 min — whisper pipeline is long

const WHISPER_URL =
  process.env.WHISPER_API_URL ||
  "https://leonardijohnson0--client-whisperer-fastapi-app.modal.run";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();

    const upstream = await fetch(`${WHISPER_URL}/whisper`, {
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
    console.error("[whisper proxy]", err);
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "Proxy error" },
      { status: 500 }
    );
  }
}
