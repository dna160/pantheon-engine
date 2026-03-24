import { NextRequest, NextResponse } from "next/server";
export const runtime = "nodejs";
export const maxDuration = 30;
const MODAL_URL = process.env.MODAL_API_URL || "https://leonardijohnson0--pantheon-engine-fastapi-app.modal.run";
export async function GET(req: NextRequest) {
  const jobId = req.nextUrl.searchParams.get("job_id");
  if (!jobId) return NextResponse.json({ error: "Missing job_id" }, { status: 400 });
  try {
    const upstream = await fetch(`${MODAL_URL}/job/${jobId}`, {
      signal: AbortSignal.timeout(25_000),
    });
    const data = await upstream.json();
    return NextResponse.json(data);
  } catch (err: unknown) {
    return NextResponse.json({ error: err instanceof Error ? err.message : "Proxy error" }, { status: 500 });
  }
}
