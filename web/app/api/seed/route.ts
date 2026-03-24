import { NextRequest, NextResponse } from "next/server";

const MODAL_URL = "https://leonardijohnson0--pantheon-engine-fastapi-app.modal.run";

export const maxDuration = 120;

export async function POST(req: NextRequest) {
  const body = await req.json();
  try {
    const res = await fetch(`${MODAL_URL}/seed`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(115_000),
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 });
  }
}
