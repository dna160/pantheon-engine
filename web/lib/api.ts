import type { PipelineConfig, PipelineResult } from "./types";

const MODAL_URL =
  process.env.NEXT_PUBLIC_MODAL_API_URL ||
  "https://leonardijohnson0--pantheon-engine-fastapi-app.modal.run";

export async function runPipeline(
  config: PipelineConfig,
  signal?: AbortSignal
): Promise<PipelineResult> {
  // Call Modal directly — CORS is open (*) on Modal and Vercel's 300s proxy
  // timeout is shorter than the pipeline runtime (can be 5-15 min for 10 agents).
  // Use a combined signal: caller's abort + 20-minute hard cap.
  const hardCap = AbortSignal.timeout(20 * 60 * 1000); // 20 min
  const combined =
    signal
      ? AbortSignal.any([signal, hardCap])
      : hardCap;

  const response = await fetch(`${MODAL_URL}/run_pipeline`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      target: config.target,
      brief: config.brief,
      client: config.client,
      limit: config.limit,
      group_size: config.groupSize,
    }),
    signal: combined,
  });

  const text = await response.text();

  let data: unknown;
  try {
    data = JSON.parse(text);
  } catch {
    throw new Error(
      `Server returned non-JSON (${response.status}): ${text.slice(0, 300)}`
    );
  }

  if (!response.ok) {
    const err =
      (data as Record<string, string>)?.error ||
      `Pipeline failed (${response.status})`;
    throw new Error(err);
  }

  // Surface Modal-wrapped errors (200 with { error: "..." })
  if ((data as Record<string, string>)?.error) {
    throw new Error((data as Record<string, string>).error);
  }

  return data as PipelineResult;
}
