"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";

interface Agent {
  id: string;
  target_demographic: string;
  age: number;
  ethnicity: string;
  current_religion: string;
  religiosity: number;
  openness: number;
  conscientiousness: number;
  extraversion: number;
  agreeableness: number;
  neuroticism: number;
  communication_style: number | string;
  decision_making: number | string;
  identity_fusion: number;
  chronesthesia_capacity: number;
  tom_self_awareness: number;
  tom_social_modeling: number;
  executive_flexibility: number;
  cumulative_cultural_capacity: number;
  persona_narrative?: string;
  cultural_primary?: string;
  cultural_secondary?: string;
  partner_culture?: string;
  origin_layer: { summary?: string } | string | null;
  created_at: string;
}

type Phase = "idle" | "seeding" | "done" | "error";

const TRAIT_COLOR = (v: number) => {
  if (v >= 70) return "text-emerald-400";
  if (v >= 45) return "text-purple-300";
  return "text-rose-400";
};

const TraitBar = ({ label, value }: { label: string; value: number }) => (
  <div className="flex items-center gap-2 text-xs">
    <span className="w-28 shrink-0 text-[11px] text-[#8888aa]">{label}</span>
    <div className="flex-1 h-1.5 rounded-full bg-[#1e1e30] overflow-hidden">
      <div
        className="h-full rounded-full bg-gradient-to-r from-[#7b61ff] to-[#a78bfa]"
        style={{ width: `${Math.min(100, value)}%` }}
      />
    </div>
    <span className={`w-8 text-right font-mono ${TRAIT_COLOR(value)}`}>{Math.round(value)}</span>
  </div>
);

function AgentCard({ agent, isNew }: { agent: Agent; isNew: boolean }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className={`rounded-xl border p-4 transition-all duration-300 cursor-pointer
        ${isNew
          ? "border-[#7b61ff]/60 bg-[#7b61ff]/10 shadow-[0_0_20px_rgba(123,97,255,0.2)]"
          : "border-[#1e1e30] bg-[#13131f] hover:border-[#7b61ff]/30"
        }`}
      onClick={() => setExpanded(!expanded)}
    >
      {/* Header row */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-white font-semibold text-sm truncate">{agent.target_demographic}</span>
            {isNew && (
              <span className="shrink-0 text-[10px] font-bold px-1.5 py-0.5 rounded-full bg-[#7b61ff]/30 text-[#a78bfa] border border-[#7b61ff]/40">
                NEW
              </span>
            )}
          </div>
          <div className="flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-[#8888aa]">
            <span>Age {agent.age}</span>
            <span>{agent.ethnicity}</span>
            {agent.current_religion && <span>{agent.current_religion}</span>}
            {(typeof agent.communication_style === "number") && (
              <>
                <span className="text-[#555577]">·</span>
                <span>Comm <span className={`font-mono ${TRAIT_COLOR(agent.communication_style as number)}`}>{Math.round(agent.communication_style as number)}</span></span>
                <span>Decide <span className={`font-mono ${TRAIT_COLOR(agent.decision_making as number)}`}>{Math.round(agent.decision_making as number)}</span></span>
              </>
            )}
            {(typeof agent.communication_style === "string" && agent.communication_style) && (
              <>
                <span className="text-[#555577]">·</span>
                <span>{agent.communication_style}</span>
                <span>{agent.decision_making}</span>
              </>
            )}
          </div>
        </div>
        <div className="flex flex-col items-end gap-1 shrink-0">
          <span className="text-[10px] text-[#555577]">
            {typeof agent.origin_layer === "object" && agent.origin_layer?.summary
              ? agent.origin_layer.summary.slice(0, 40) + "…"
              : typeof agent.origin_layer === "string"
              ? agent.origin_layer.slice(0, 40)
              : ""}
          </span>
          <span className="text-[10px] text-[#555577]">
            {new Date(agent.created_at).toLocaleDateString()}
          </span>
        </div>
      </div>

      {/* Big Five quick view */}
      <div className="mt-3 grid grid-cols-5 gap-1">
        {[
          ["O", agent.openness],
          ["C", agent.conscientiousness],
          ["E", agent.extraversion],
          ["A", agent.agreeableness],
          ["N", agent.neuroticism],
        ].map(([label, val]) => (
          <div key={label as string} className="flex flex-col items-center">
            <span className={`text-sm font-bold font-mono ${TRAIT_COLOR(val as number)}`}>
              {Math.round(val as number)}
            </span>
            <span className="text-[9px] text-[#555577]">{label}</span>
          </div>
        ))}
      </div>

      {/* Expanded traits */}
      {expanded && (
        <div className="mt-4 pt-4 border-t border-[#1e1e30] space-y-2">

          {/* Persona Narrative */}
          {agent.persona_narrative && (
            <div className="mb-4 p-3 rounded-lg bg-[#0a0a0f] border border-[#7b61ff]/20">
              <p className="text-[10px] font-semibold text-[#7b61ff] uppercase tracking-widest mb-1.5">Persona</p>
              <p className="text-[11px] text-[#ccccdd] leading-relaxed">{agent.persona_narrative}</p>
            </div>
          )}

          {/* Cultural Identity */}
          {(agent.cultural_primary || agent.cultural_secondary || agent.partner_culture) && (
            <div className="mb-4 space-y-1.5">
              <p className="text-[10px] font-semibold text-[#f59e0b] uppercase tracking-widest mb-1.5">Cultural Identity</p>
              {agent.cultural_primary && (
                <p className="text-[11px] text-[#ccccdd]"><span className="text-[#8888aa]">Primary: </span>{agent.cultural_primary}</p>
              )}
              {agent.cultural_secondary && agent.cultural_secondary !== "None" && (
                <p className="text-[11px] text-[#ccccdd]"><span className="text-[#8888aa]">Secondary: </span>{agent.cultural_secondary}</p>
              )}
              {agent.partner_culture && (
                <p className="text-[11px] text-[#ccccdd]"><span className="text-[#8888aa]">Partner: </span>{agent.partner_culture}</p>
              )}
            </div>
          )}

          {/* PANTHEON Cognitive Dimensions */}
          <p className="text-[11px] font-semibold text-[#7b61ff] uppercase tracking-widest mb-3">
            PANTHEON Cognitive Dimensions
          </p>
          <TraitBar label="Cultural Capacity" value={agent.cumulative_cultural_capacity ?? 0} />
          <TraitBar label="Identity Fusion" value={agent.identity_fusion} />
          <TraitBar label="Chronesthesia" value={agent.chronesthesia_capacity} />
          <TraitBar label="ToM Self-Aware" value={agent.tom_self_awareness} />
          <TraitBar label="ToM Social" value={agent.tom_social_modeling} />
          <TraitBar label="Exec Flexibility" value={agent.executive_flexibility} />

          {/* Big Five */}
          <p className="text-[11px] font-semibold text-[#7b61ff] uppercase tracking-widest mb-3 mt-4">
            Big Five
          </p>
          <TraitBar label="Openness" value={agent.openness} />
          <TraitBar label="Conscientiousness" value={agent.conscientiousness} />
          <TraitBar label="Extraversion" value={agent.extraversion} />
          <TraitBar label="Agreeableness" value={agent.agreeableness} />
          <TraitBar label="Neuroticism" value={agent.neuroticism} />

          {typeof agent.communication_style === "number" && (
            <>
              <p className="text-[11px] font-semibold text-[#7b61ff] uppercase tracking-widest mb-3 mt-4">
                Behavioral
              </p>
              <TraitBar label="Communication" value={agent.communication_style as number} />
              <TraitBar label="Decision Making" value={agent.decision_making as number} />
            </>
          )}
        </div>
      )}
    </div>
  );
}

export default function SeedPage() {
  const [demographic, setDemographic] = useState("Medanese Upper Middle Class, 25-45");
  const [count, setCount] = useState(10);
  const [ageMin, setAgeMin] = useState(18);
  const [ageMax, setAgeMax] = useState(35);
  const [filterQuery, setFilterQuery] = useState("");

  const [phase, setPhase] = useState<Phase>("idle");
  const [error, setError] = useState("");
  const [newAgentIds, setNewAgentIds] = useState<Set<string>>(new Set());

  const [agents, setAgents] = useState<Agent[]>([]);
  const [totalAgents, setTotalAgents] = useState<number | null>(null);
  const [loadingAgents, setLoadingAgents] = useState(false);

  const fetchAgents = useCallback(async (query?: string) => {
    setLoadingAgents(true);
    try {
      const params = new URLSearchParams({ limit: "100" });
      const q = query !== undefined ? query : filterQuery;
      if (q.trim()) params.set("demographic", q.trim());
      const res = await fetch(`/api/agents?${params}`);
      const data = await res.json();
      setAgents(data.agents ?? []);
      setTotalAgents(data.total ?? 0);
    } catch {
      // silently fail — DB may be cold
    } finally {
      setLoadingAgents(false);
    }
  }, [filterQuery]);

  useEffect(() => {
    fetchAgents();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSeed = async () => {
    if (!demographic.trim() || phase === "seeding") return;
    setPhase("seeding");
    setError("");
    setNewAgentIds(new Set());

    try {
      const res = await fetch("/api/seed", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          demographic: demographic.trim(),
          count,
          age_min: ageMin,
          age_max: ageMax,
        }),
      });

      // Vercel serverless functions can time out before Modal finishes,
      // even though agents were written to Supabase. Treat timeout as
      // a soft warning rather than a hard error.
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        const msg = data?.error ?? `HTTP ${res.status}`;
        const isTimeout = msg.includes("TimeoutError") || msg.includes("timeout") || res.status === 504;
        if (isTimeout) {
          setError("Modal is still seeding — agents may take a moment to appear. Refreshing list…");
        } else {
          setError(msg);
        }
        setPhase("error");
        return;
      }

      const data = await res.json();
      const seededIds = new Set<string>(
        (data.agents as Agent[] ?? []).map((a) => a.id)
      );
      setNewAgentIds(seededIds);
      setPhase("done");
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      const isTimeout = msg.includes("TimeoutError") || msg.includes("timeout") || msg.includes("abort");
      setError(
        isTimeout
          ? "Request timed out — Modal may still be seeding. Refreshing list…"
          : msg
      );
      setPhase("error");
    } finally {
      // Always refresh the agent list regardless of success/failure —
      // agents may have been written to Supabase even if the response timed out.
      await fetchAgents(filterQuery);
    }
  };

  const handleFilterChange = (q: string) => {
    setFilterQuery(q);
    fetchAgents(q);
  };

  const isSeeding = phase === "seeding";

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-white">
      <div className="max-w-5xl mx-auto px-6 py-10">

        {/* Header */}
        <div className="flex items-start justify-between mb-8">
          <div>
            <div className="text-xs font-semibold tracking-[4px] text-[#10b981] uppercase mb-2">
              Agent Genesis
            </div>
            <h1 className="text-4xl font-black tracking-tight text-white mb-2">
              Seed Agents
            </h1>
            <p className="text-[#8888aa] text-[15px]">
              Generate synthetic personality genomes · Populate the PANTHEON agent pool
            </p>
          </div>
          <Link
            href="/"
            className="shrink-0 flex items-center gap-2 px-4 py-2 rounded-xl border border-[#7b61ff]/40 bg-[#7b61ff]/10 text-[#a78bfa] text-sm font-semibold hover:bg-[#7b61ff]/20 hover:border-[#7b61ff]/60 transition-all duration-200 mt-1"
          >
            <span className="text-[#7b61ff]/60">←</span>PANTHEON<span>⚡</span>
          </Link>
        </div>

        <hr className="border-[#1e1e30] mb-8" />

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

          {/* ── Seed Form ── */}
          <div className="lg:col-span-1 space-y-5">
            <div className="bg-[#13131f] rounded-2xl border border-[#1e1e30] p-5">
              <h2 className="text-sm font-bold text-white mb-4 uppercase tracking-widest">
                Seed Configuration
              </h2>

              {/* Demographic */}
              <div className="mb-4">
                <label className="block text-xs text-[#8888aa] mb-1.5 font-medium">
                  Target Demographic
                </label>
                <textarea
                  className="w-full bg-[#0a0a0f] border border-[#1e1e30] rounded-lg px-3 py-2.5 text-sm text-white placeholder-[#555577] focus:outline-none focus:border-[#7b61ff]/50 resize-none"
                  rows={3}
                  value={demographic}
                  onChange={(e) => setDemographic(e.target.value)}
                  placeholder="e.g. Urban Millennial Jakarta, 28-38, tech-savvy professional"
                  disabled={isSeeding}
                />
              </div>

              {/* Count */}
              <div className="mb-4">
                <label className="block text-xs text-[#8888aa] mb-1.5 font-medium">
                  Agents to Generate
                  <span className="ml-2 text-[#7b61ff] font-bold">{count}</span>
                </label>
                <input
                  type="range"
                  min={1}
                  max={50}
                  value={count}
                  onChange={(e) => setCount(Number(e.target.value))}
                  disabled={isSeeding}
                  className="w-full accent-[#7b61ff]"
                />
                <div className="flex justify-between text-[10px] text-[#555577] mt-1">
                  <span>1</span><span>25</span><span>50</span>
                </div>
              </div>

              {/* Age range */}
              <div className="mb-5">
                <label className="block text-xs text-[#8888aa] mb-1.5 font-medium">
                  Age Range
                  <span className="ml-2 text-[#7b61ff] font-bold">{ageMin}–{ageMax}</span>
                </label>
                <div className="flex gap-2">
                  <div className="flex-1">
                    <input
                      type="number"
                      min={10}
                      max={ageMax - 1}
                      value={ageMin}
                      onChange={(e) => setAgeMin(Number(e.target.value))}
                      disabled={isSeeding}
                      className="w-full bg-[#0a0a0f] border border-[#1e1e30] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-[#7b61ff]/50"
                    />
                    <div className="text-[10px] text-[#555577] mt-1 text-center">Min</div>
                  </div>
                  <div className="flex-1">
                    <input
                      type="number"
                      min={ageMin + 1}
                      max={90}
                      value={ageMax}
                      onChange={(e) => setAgeMax(Number(e.target.value))}
                      disabled={isSeeding}
                      className="w-full bg-[#0a0a0f] border border-[#1e1e30] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-[#7b61ff]/50"
                    />
                    <div className="text-[10px] text-[#555577] mt-1 text-center">Max</div>
                  </div>
                </div>
              </div>

              {/* Seed button */}
              <button
                onClick={handleSeed}
                disabled={!demographic.trim() || isSeeding}
                className={`w-full py-3 rounded-xl font-bold text-sm tracking-wide transition-all duration-200
                  ${!demographic.trim() || isSeeding
                    ? "bg-[#13131f] border border-[#1e1e30] text-[#555577] cursor-not-allowed"
                    : "bg-gradient-to-r from-[#10b981] to-[#059669] text-white shadow-[0_4px_20px_rgba(16,185,129,0.3)] hover:-translate-y-0.5 hover:shadow-[0_8px_28px_rgba(16,185,129,0.45)]"
                  }`}
              >
                {isSeeding ? (
                  <span className="flex items-center justify-center gap-2">
                    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
                    </svg>
                    Generating genomes…
                  </span>
                ) : (
                  `⚡ Seed ${count} Agent${count !== 1 ? "s" : ""}`
                )}
              </button>

              {/* Status feedback */}
              {phase === "done" && (
                <div className="mt-3 text-center text-xs text-[#10b981] font-semibold">
                  ✓ {newAgentIds.size} agent{newAgentIds.size !== 1 ? "s" : ""} seeded successfully
                </div>
              )}
              {phase === "error" && (
                <div className="mt-3 p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs">
                  {error}
                </div>
              )}
            </div>

            {/* Pool stats */}
            <div className="bg-[#13131f] rounded-2xl border border-[#1e1e30] p-5">
              <h3 className="text-xs font-bold text-[#8888aa] uppercase tracking-widest mb-3">
                Agent Pool
              </h3>
              <div className="text-3xl font-black text-white mb-1">
                {totalAgents === null ? (
                  <span className="text-[#555577] text-xl">—</span>
                ) : (
                  totalAgents.toLocaleString()
                )}
              </div>
              <div className="text-xs text-[#555577]">
                {filterQuery ? `matching "${filterQuery}"` : "total agents in Supabase"}
              </div>
            </div>
          </div>

          {/* ── Agent List ── */}
          <div className="lg:col-span-2">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-bold text-white uppercase tracking-widest">
                Agent Genomes
              </h2>
              <button
                onClick={() => fetchAgents()}
                disabled={loadingAgents}
                className="text-xs text-[#7b61ff] hover:text-[#a78bfa] transition-colors disabled:opacity-50"
              >
                {loadingAgents ? "Loading…" : "↻ Refresh"}
              </button>
            </div>

            {/* Filter */}
            <input
              type="text"
              className="w-full bg-[#13131f] border border-[#1e1e30] rounded-lg px-3 py-2 text-sm text-white placeholder-[#555577] focus:outline-none focus:border-[#7b61ff]/50 mb-4"
              placeholder="Filter by demographic…"
              value={filterQuery}
              onChange={(e) => handleFilterChange(e.target.value)}
            />

            {/* Cards */}
            {agents.length === 0 && !loadingAgents ? (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <div className="text-4xl mb-4">🧬</div>
                <div className="text-[#8888aa] text-sm">
                  {filterQuery ? "No agents match this filter." : "No agents yet. Seed some above."}
                </div>
              </div>
            ) : loadingAgents && agents.length === 0 ? (
              <div className="flex items-center justify-center py-16">
                <svg className="animate-spin h-6 w-6 text-[#7b61ff]" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
                </svg>
              </div>
            ) : (
              <div className="space-y-3 max-h-[70vh] overflow-y-auto pr-1">
                {agents.map((agent) => (
                  <AgentCard
                    key={agent.id}
                    agent={agent}
                    isNew={newAgentIds.has(agent.id)}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
