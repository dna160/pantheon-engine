"use client";

import React, { useState, useRef, useEffect, useCallback } from "react";
import Sidebar from "@/components/Sidebar";
import BriefInput from "@/components/BriefInput";
import PipelineViz, { makeInitialNodes, tickNodes } from "@/components/PipelineViz";
import ResultsPanel from "@/components/ResultsPanel";
import type { NodeState, CampaignEntry } from "@/lib/types";
import { runPipeline } from "@/lib/api";
import { loadHistory, appendHistory } from "@/lib/history";

type Phase = "idle" | "running" | "done" | "error";

export default function Home() {
  // ── Config state ────────────────────────────────────────────────────────────
  const [clientName, setClientName] = useState("");
  const [ptm, setPtm]   = useState("Medanese Upper Middle Class, 25-45");
  const [stm, setStm]   = useState("");
  const [agentLimit, setAgentLimit] = useState(10);
  const [groupSize, setGroupSize]   = useState(5);
  const [brief, setBrief] = useState("");

  // ── Pipeline state ──────────────────────────────────────────────────────────
  const [phase, setPhase]         = useState<Phase>("idle");
  const [nodes, setNodes]         = useState<NodeState[]>(makeInitialNodes());
  const [logs, setLogs]           = useState<string[]>([]);
  const [statusText, setStatusText] = useState("Ready to launch.");
  const [elapsed, setElapsed]     = useState(0);
  const [report, setReport]       = useState("");
  const [errorMsg, setErrorMsg]   = useState("");

  // ── History ─────────────────────────────────────────────────────────────────
  const [history, setHistory] = useState<CampaignEntry[]>([]);
  const [showHistory, setShowHistory] = useState(false);

  const abortRef  = useRef<AbortController | null>(null);
  const timerRef  = useRef<ReturnType<typeof setInterval> | null>(null);
  const startRef  = useRef<number>(0);

  useEffect(() => {
    setHistory(loadHistory());
  }, []);

  // Tick elapsed + animate node progress + inject phase-aware status messages
  const loggedMilestonesRef = useRef<Set<number>>(new Set());
  useEffect(() => {
    if (phase === "running") {
      loggedMilestonesRef.current = new Set();
      timerRef.current = setInterval(() => {
        const secs = Math.floor((Date.now() - startRef.current) / 1000);
        setElapsed(secs);
        setNodes((prev) => tickNodes(prev, secs, agentLimit, groupSize));

        // Inject informational logs at key milestones so the user knows it's alive
        const milestones: Record<number, string> = {
          15:  "[NODE 1] Querying Supabase agent pool...",
          45:  "[NODE 2] Generating runtime snapshots — waking agents...",
          90:  "[NODE 3] Phase A: Mass session underway — collecting gut reactions...",
          180: "[NODE 3] Phase A still running — large agent pools take 3-5 min...",
          240: "[NODE 4] Breakout rooms forming — debate generation in progress...",
          300: "[NODE 4] Still in breakout — complex groups can take 5-8 min total...",
          420: "[NODE 5] Synthesis underway — generating intelligence report...",
          540: "[NODE 5] Report generation in progress — almost there...",
        };
        if (milestones[secs] && !loggedMilestonesRef.current.has(secs)) {
          loggedMilestonesRef.current.add(secs);
          setLogs((prev) => [...prev, milestones[secs]]);
          setStatusText(milestones[secs].replace(/^\[.*?\]\s*/, ""));
        }
      }, 1000);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [phase, agentLimit, groupSize]);

  function handleConfigChange(field: string, value: string | number) {
    if (field === "clientName") setClientName(value as string);
    if (field === "ptm")        setPtm(value as string);
    if (field === "stm")        setStm(value as string);
    if (field === "agentLimit") setAgentLimit(value as number);
    if (field === "groupSize")  setGroupSize(value as number);
  }

  const handleExecute = useCallback(async () => {
    if (brief.length <= 50 || phase === "running") return;

    setPhase("running");
    setElapsed(0);
    setReport("");
    setErrorMsg("");
    setNodes(makeInitialNodes());
    startRef.current = Date.now();

    const target = stm.trim()
      ? `${ptm.trim()}|${stm.trim()}`
      : ptm.trim();

    const initLogs = [
      "[SYSTEM] Booting PANTHEON Core...",
      "[MODERATOR] Waking up. Awaiting target demographics.",
      `[SYSTEM] Target: ${target}`,
      `[SYSTEM] Agents: ${agentLimit} · Group size: ${groupSize}`,
      "[SYSTEM] Dispatching to Modal serverless infrastructure...",
    ];
    setLogs(initLogs);
    setStatusText("Phase 1: Connecting to Modal — querying Supabase...");

    abortRef.current = new AbortController();

    try {
      const result = await runPipeline(
        { brief, target, client: clientName, limit: agentLimit, groupSize },
        abortRef.current.signal
      );

      const finalElapsed = Math.floor((Date.now() - startRef.current) / 1000);
      setElapsed(finalElapsed);

      if (result.status === "success" && result.report) {
        setNodes((prev) => prev.map((n) => ({ ...n, status: "complete" })));
        setLogs((prev) => [...prev, "[SYSTEM] Pipeline complete. Report generated."]);
        setStatusText("Complete ✓");
        setReport(result.report);
        setPhase("done");

        const entry: CampaignEntry = {
          id: Date.now().toString(),
          timestamp: new Date().toISOString(),
          client: clientName,
          target,
          brief: brief.slice(0, 200),
          elapsed: finalElapsed,
          report: result.report,
        };
        appendHistory(entry);
        setHistory(loadHistory());
      } else {
        throw new Error(result.error || "Pipeline returned no report");
      }
    } catch (err: unknown) {
      if (err instanceof Error && err.name === "AbortError") {
        setLogs((prev) => [...prev, "[SYSTEM] Pipeline cancelled by user."]);
        setStatusText("Cancelled.");
        setPhase("idle");
        setNodes(makeInitialNodes());
        return;
      }
      const msg = err instanceof Error ? err.message : String(err);
      setErrorMsg(msg);
      setLogs((prev) => [...prev, `[ERROR] ${msg}`]);
      setStatusText("Pipeline failed — see error below.");
      setPhase("error");
      setNodes((prev) => prev.map((n) => n.status === "running" ? { ...n, status: "error" } : n));
    }
  }, [brief, phase, ptm, stm, clientName, agentLimit, groupSize]);

  function handleKill() {
    abortRef.current?.abort();
  }

  const briefReady = brief.length > 50;
  const isRunning  = phase === "running";

  return (
    <div className="flex h-screen overflow-hidden bg-bg">
      {/* Sidebar */}
      <Sidebar
        clientName={clientName}
        ptm={ptm}
        stm={stm}
        agentLimit={agentLimit}
        groupSize={groupSize}
        onChange={handleConfigChange}
        isRunning={isRunning}
      />

      {/* Main scrollable content */}
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-8 py-10">

          {/* ── Page header ── */}
          <div className="flex items-start justify-between mb-8">
            <div>
              <div className="text-xs font-semibold tracking-[4px] text-purple uppercase mb-2">
                Market Research Intelligence
              </div>
              <h1 className="text-4xl font-black tracking-tight text-white mb-2">
                PANTHEON
              </h1>
              <p className="text-text-dim text-[15px]">
                Synthetic focus groups · Parallel LLM agents · Actionable research reports
              </p>
            </div>
            <div className="flex flex-col gap-2 mt-1">
              <a
                href="/whisperer"
                className="shrink-0 flex items-center gap-2 px-4 py-2 rounded-xl border border-amber/40 bg-amber/10 text-amber text-sm font-semibold hover:bg-amber/20 hover:border-amber/60 transition-all duration-200"
              >
                <span>🧠</span>
                Human Whisperer
                <span className="text-amber/60">→</span>
              </a>
              <a
                href="/seed"
                className="shrink-0 flex items-center gap-2 px-4 py-2 rounded-xl border border-emerald-500/40 bg-emerald-500/10 text-emerald-400 text-sm font-semibold hover:bg-emerald-500/20 hover:border-emerald-500/60 transition-all duration-200"
              >
                <span>🧬</span>
                Seed Agents
                <span className="text-emerald-400/60">→</span>
              </a>
            </div>
          </div>

          <hr className="border-border mb-8" />

          {/* ── Brief Input ── */}
          <div className="mb-8">
            <BriefInput value={brief} onChange={setBrief} disabled={isRunning} />
          </div>

          <hr className="border-border mb-8" />

          {/* ── Execute section ── */}
          <div className="mb-8">
            <h2 className="text-lg font-bold text-white mb-4">🚀 Execute Pipeline</h2>
            <div className="flex gap-3 items-center justify-center">
              <button
                onClick={handleExecute}
                disabled={!briefReady || isRunning}
                className={`
                  px-10 py-3.5 rounded-xl font-bold text-base tracking-wide transition-all duration-200
                  ${briefReady && !isRunning
                    ? "bg-gradient-to-r from-purple-deep to-purple text-white shadow-[0_4px_20px_rgba(123,97,255,0.4)] hover:-translate-y-0.5 hover:shadow-[0_8px_28px_rgba(123,97,255,0.55)]"
                    : "bg-card border border-border text-text-dim cursor-not-allowed opacity-60"
                  }
                `}
              >
                {isRunning ? (
                  <span className="flex items-center gap-2">
                    <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Running…
                  </span>
                ) : (
                  "⚡  Execute Genesis Protocol"
                )}
              </button>

              {isRunning && (
                <button
                  onClick={handleKill}
                  className="px-6 py-3.5 rounded-xl font-bold text-sm bg-gradient-to-r from-red-deep to-red text-white shadow-[0_4px_20px_rgba(220,38,38,0.35)] hover:-translate-y-0.5 hover:shadow-[0_6px_24px_rgba(220,38,38,0.55)] transition-all duration-200"
                >
                  🛑 Kill Process
                </button>
              )}
            </div>

            {!briefReady && !isRunning && (
              <p className="text-center text-text-dim text-xs mt-3">
                Enter a campaign brief (&gt;50 chars) to activate.
              </p>
            )}
          </div>

          {/* ── Error banner ── */}
          {phase === "error" && errorMsg && (
            <div className="mb-8 p-4 rounded-xl bg-red-900/20 border border-red-500/40 text-red-300 text-sm animate-fadeIn">
              <strong>Pipeline error:</strong> {errorMsg}
            </div>
          )}

          {/* ── Pipeline visualization ── */}
          {(isRunning || phase === "done" || phase === "error") && (
            <div className="mb-8 bg-card border border-border rounded-2xl p-6">
              <PipelineViz
                nodes={nodes}
                logs={logs}
                statusText={statusText}
                isRunning={isRunning}
                elapsedSeconds={elapsed}
              />
            </div>
          )}

          {/* ── Results ── */}
          {phase === "done" && report && (
            <div className="mb-8 bg-card border border-border rounded-2xl p-6">
              <ResultsPanel
                report={report}
                elapsed={elapsed}
                client={clientName}
                target={ptm}
                brief={brief}
              />
            </div>
          )}

          {/* ── Campaign History ── */}
          {history.length > 0 && (
            <div className="mb-8">
              <button
                onClick={() => setShowHistory((v) => !v)}
                className="flex items-center gap-2 text-sm font-semibold text-text-dim hover:text-text-muted transition-colors"
              >
                <span>{showHistory ? "▾" : "▸"}</span>
                Campaign History ({history.length})
              </button>

              {showHistory && (
                <div className="mt-3 space-y-2 animate-fadeIn">
                  {history.map((entry) => (
                    <div
                      key={entry.id}
                      className="bg-card border border-border rounded-xl p-4 cursor-pointer hover:border-border-hover transition-colors"
                      onClick={() => { setReport(entry.report); setPhase("done"); setElapsed(entry.elapsed); setClientName(entry.client); setPtm(entry.target.split("|")[0]); }}
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <span className="text-sm font-semibold text-text-primary">
                            {entry.client || "Unnamed"} — {entry.target}
                          </span>
                          <p className="text-xs text-text-dim mt-0.5">
                            {new Date(entry.timestamp).toLocaleString()} · {entry.elapsed}s
                          </p>
                        </div>
                        <span className="text-xs px-2 py-0.5 rounded bg-green/15 border border-green/30 text-green">
                          Load
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
