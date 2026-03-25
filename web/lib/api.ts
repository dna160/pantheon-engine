import type { PipelineConfig, PipelineResult } from "./types";

export async function runPipeline(
  config: PipelineConfig,
  signal?: AbortSignal
): Promise<PipelineResult> {
  // Step 1: Start the pipeline job (returns job_id immediately)
  const startRes = await fetch("/api/pipeline", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      target: config.target,
      brief: config.brief,
      client: config.client,
      limit: config.limit,
      group_size: config.groupSize,
      brief_images: config.briefImages ?? [],
    }),
    signal,
  });

  if (!startRes.ok) {
    const text = await startRes.text();
    throw new Error(`Failed to start pipeline (${startRes.status}): ${text.slice(0, 300)}`);
  }

  const { job_id } = await startRes.json();
  if (!job_id) throw new Error("No job_id returned from pipeline start");

  // Step 2: Poll until done
  const deadline = Date.now() + 25 * 60 * 1000; // 25 min hard cap
  while (Date.now() < deadline) {
    if (signal?.aborted) throw new DOMException("Aborted", "AbortError");

    await new Promise((r) => setTimeout(r, 5000)); // poll every 5s
    if (signal?.aborted) throw new DOMException("Aborted", "AbortError");

    const pollRes = await fetch(`/api/pipeline/status?job_id=${job_id}`, { signal });
    if (!pollRes.ok) continue; // transient poll error — keep trying

    const data = await pollRes.json() as Record<string, unknown>;

    if (data.status === "done" || (data.status === "success" && data.report)) {
      return data as unknown as PipelineResult;
    }
    if (data.status === "error") {
      throw new Error((data.error as string) || "Pipeline failed");
    }
    if (data.status === "not_found") {
      throw new Error("Job not found — pipeline may have crashed on startup");
    }
    // status === "running" → keep polling
  }

  throw new Error("Pipeline timed out after 25 minutes");
}
