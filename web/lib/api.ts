import type { PipelineConfig, PipelineResult } from "./types";

export async function runPipeline(
  config: PipelineConfig,
  signal?: AbortSignal
): Promise<PipelineResult> {
  // Route through Vercel API proxy — avoids browser timeout on long pipeline runs
  // and bypasses any CORS issues with Modal directly.
  const response = await fetch("/api/pipeline", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      target: config.target,
      brief: config.brief,
      client: config.client,
      limit: config.limit,
      group_size: config.groupSize,
    }),
    signal,
  });

  const text = await response.text();

  let data: unknown;
  try {
    data = JSON.parse(text);
  } catch {
    throw new Error(`Server returned non-JSON (${response.status}): ${text.slice(0, 300)}`);
  }

  if (!response.ok) {
    const err = (data as Record<string, string>)?.error || `Pipeline failed (${response.status})`;
    throw new Error(err);
  }

  // Surface any error returned inside a 200 payload (Modal error wrapping)
  if ((data as Record<string, string>)?.error) {
    throw new Error((data as Record<string, string>).error);
  }

  return data as PipelineResult;
}
