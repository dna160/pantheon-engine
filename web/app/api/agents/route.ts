import { NextRequest, NextResponse } from "next/server";

const MODAL_URL = "https://leonardijohnson0--pantheon-engine-fastapi-app.modal.run";

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const demographic = searchParams.get("demographic") ?? "";
  const limit = searchParams.get("limit") ?? "50";

  const params = new URLSearchParams({ limit });
  if (demographic) params.set("demographic", demographic);

  try {
    const res = await fetch(`${MODAL_URL}/agents?${params}`, {
      signal: AbortSignal.timeout(30_000),
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 });
  }
}
