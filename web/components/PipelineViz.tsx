"use client";

import React, { useEffect, useState } from "react";
import type { NodeState } from "@/lib/types";

interface PipelineVizProps {
  nodes: NodeState[];
  logs: string[];
  statusText: string;
  isRunning: boolean;
  elapsedSeconds: number;
}

const NODE_COLORS: Record<string, { bg: string; border: string; glow: string; text: string }> = {
  idle:     { bg: "bg-card",       border: "border-border",          glow: "",                          text: "text-text-dim" },
  running:  { bg: "bg-purple/10",  border: "border-purple",          glow: "shadow-[0_0_16px_rgba(123,97,255,0.4)]", text: "text-purple" },
  complete: { bg: "bg-green/10",   border: "border-green",           glow: "shadow-[0_0_12px_rgba(16,185,129,0.3)]", text: "text-green" },
  error:    { bg: "bg-red-900/20", border: "border-red-500",         glow: "",                          text: "text-red-400" },
};

function NodeCard({ node }: { node: NodeState }) {
  const c = NODE_COLORS[node.status];

  return (
    <div
      className={`rounded-xl border p-3 transition-all duration-500 ${c.bg} ${c.border} ${c.glow}`}
    >
      <div className="flex items-center gap-2">
        {/* Status icon */}
        <div className="w-7 h-7 rounded-full flex items-center justify-center shrink-0 text-sm">
          {node.status === "idle"     && <span className="text-text-dim">○</span>}
          {node.status === "running"  && <div className="w-3.5 h-3.5 border-2 border-purple border-t-transparent rounded-full animate-spin" />}
          {node.status === "complete" && <span className="text-green">✓</span>}
          {node.status === "error"    && <span className="text-red-400">✗</span>}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-baseline gap-2">
            <span className={`text-[10px] font-black tracking-wider uppercase ${c.text}`}>
              Node {node.id}
            </span>
            <span className="text-[11px] font-semibold text-text-primary truncate">{node.label}</span>
          </div>
          <p className="text-[11px] text-text-dim truncate">{node.description}</p>
          {node.detail && node.status === "running" && (
            <p className="text-[10px] text-purple mt-0.5 truncate animate-pulse_slow">{node.detail}</p>
          )}
        </div>

        {/* Phase badge */}
        <span className={`text-[9px] font-bold tracking-widest px-1.5 py-0.5 rounded border shrink-0 ${
          node.status === "complete" ? "bg-green/15 border-green/30 text-green" :
          node.status === "running"  ? "bg-purple/15 border-purple/30 text-purple" :
          "bg-card border-border text-text-dim"
        }`}>
          {node.phase}
        </span>
      </div>
    </div>
  );
}

function ElapsedTimer({ seconds }: { seconds: number }) {
  const m = Math.floor(seconds / 60).toString().padStart(2, "0");
  const s = (seconds % 60).toString().padStart(2, "0");
  return <span className="font-mono text-purple">{m}:{s}</span>;
}

export default function PipelineViz({ nodes, logs, statusText, isRunning, elapsedSeconds }: PipelineVizProps) {
  const completedCount = nodes.filter((n) => n.status === "complete").length;
  const progress = Math.round((completedCount / nodes.length) * 100);

  return (
    <div className="animate-fadeIn">
      {/* Header strip */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-bold text-white">🔄 Pipeline Execution</h3>
          <p className="text-xs text-text-dim mt-0.5">{statusText}</p>
        </div>
        <div className="text-right">
          {isRunning && (
            <div className="text-xs text-text-dim">
              Elapsed: <ElapsedTimer seconds={elapsedSeconds} />
            </div>
          )}
          <div className="text-xs text-text-dim mt-0.5">{completedCount}/{nodes.length} nodes</div>
        </div>
      </div>

      {/* Progress bar */}
      <div className="h-1.5 bg-card border border-border rounded-full overflow-hidden mb-4">
        <div
          className="h-full bg-gradient-to-r from-purple-deep to-purple rounded-full transition-all duration-700"
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Node grid */}
      <div className="grid grid-cols-1 gap-2 mb-4">
        {nodes.map((node) => (
          <NodeCard key={node.id} node={node} />
        ))}
      </div>

      {/* Live log */}
      {logs.length > 0 && (
        <div>
          <div className="text-[10px] font-semibold tracking-widest text-text-dim uppercase mb-1.5">
            System Log
          </div>
          <div className="bg-bg border border-border rounded-xl p-3 h-40 overflow-y-auto font-mono text-[11px] text-text-muted space-y-0.5">
            {logs.slice(-30).map((line, i) => (
              <div key={i} className={line.startsWith("[MODERATOR]") ? "text-purple" : line.startsWith("[SYSTEM]") ? "text-green" : "text-text-dim"}>
                {line}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Utilities exported for the parent page ──────────────────────────────────

export function makeInitialNodes(): NodeState[] {
  return [
    { id: 1, label: "Intake & Query",          phase: "Phase 1", description: "Load agent genomes from Supabase",        status: "idle" },
    { id: 2, label: "Swarm Assembly",           phase: "Phase 2", description: "Generate runtime emotional snapshots",    status: "idle" },
    { id: 3, label: "Mass Session — Phase A",   phase: "Phase 3", description: "Broadcast brief; capture gut reactions",  status: "idle" },
    { id: 4, label: "Breakout Rooms — Phase B", phase: "Phase 4", description: "Parallel focus group debates",            status: "idle" },
    { id: 5, label: "Synthesis — Phase C",      phase: "Phase 5", description: "Claude Sonnet writes PANTHEON report",   status: "idle" },
    { id: 6, label: "Presentation Architect",   phase: "Phase 6", description: "Build slide deck (pptxgenjs)",           status: "idle" },
    { id: 7, label: "Client Whisperer",         phase: "Phase 7", description: "Draft meeting prep document",            status: "idle" },
  ];
}

export function tickNodes(
  prev: NodeState[],
  elapsedSeconds: number,
  agentLimit: number,
  groupSize: number
): NodeState[] {
  // Rough time budget per node (seconds) based on config
  const nGroups = Math.max(1, Math.ceil(agentLimit / groupSize));
  const budget = [
    15,                    // Node 1: query
    20,                    // Node 2: snapshots
    25,                    // Node 3: mass session
    nGroups * 55,          // Node 4: breakout rooms
    40,                    // Node 5: synthesis
    30,                    // Node 6: deck
    20,                    // Node 7: whisperer
  ];

  let cursor = 0;
  return prev.map((node, i) => {
    const start = cursor;
    const end = cursor + budget[i];
    cursor = end;

    if (elapsedSeconds < start) return { ...node, status: "idle" };
    if (elapsedSeconds >= start && elapsedSeconds < end) return { ...node, status: "running", detail: "Processing…" };
    return { ...node, status: "complete" };
  });
}
