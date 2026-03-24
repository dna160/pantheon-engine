import type { PipelineConfig, PipelineResult } from "./types";

const MODAL_URL =
  process.env.NEXT_PUBLIC_MODAL_API_URL ||
  "https://leonardijohnson0--pantheon-engine-fastapi-app.modal.run";

export async function runPipeline(
  config: PipelineConfig,
  signal?: AbortSignal
): Promise<PipelineResult> {
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
    signal,
  });

  if (!response.ok) {
    const text = await response.text().catch(() => "Unknown error");
    throw new Error(`Pipeline failed (${response.status}): ${text}`);
  }

  return response.json();
}
