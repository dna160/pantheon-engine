"use client";

import React from "react";

interface SidebarProps {
  clientName: string;
  ptm: string;
  stm: string;
  agentLimit: number;
  groupSize: number;
  onChange: (field: string, value: string | number) => void;
  isRunning: boolean;
}

export default function Sidebar({
  clientName,
  ptm,
  stm,
  agentLimit,
  groupSize,
  onChange,
  isRunning,
}: SidebarProps) {
  const nGroups = Math.max(1, Math.ceil(agentLimit / groupSize));
  const estMin = ((30 + nGroups * 60 + 45) / 60).toFixed(1);

  return (
    <aside className="w-72 shrink-0 bg-card border-r border-border flex flex-col h-screen overflow-y-auto">
      {/* Logo */}
      <div className="flex flex-col items-center py-7 px-6 border-b border-border">
        <span className="text-4xl mb-2">⚡</span>
        <div className="text-lg font-black tracking-[4px] text-white">PANTHEON</div>
        <div className="text-[10px] tracking-[3px] text-text-dim mt-0.5">INTELLIGENCE ENGINE</div>
      </div>

      {/* Config */}
      <div className="flex-1 px-5 py-6 space-y-5">
        <h2 className="text-xs font-bold tracking-[2px] text-text-dim uppercase">
          ⚙️ Run Configuration
        </h2>

        {/* Client Name */}
        <div>
          <label className="block text-[10px] font-semibold tracking-[2px] text-green mb-1.5">
            CLIENT NAME
          </label>
          <input
            type="text"
            value={clientName}
            onChange={(e) => onChange("clientName", e.target.value)}
            disabled={isRunning}
            placeholder="e.g. Yakun (Optional)"
            className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-sm text-text-primary placeholder-text-dim focus:outline-none focus:border-purple focus:ring-1 focus:ring-purple/40 disabled:opacity-50"
          />
        </div>

        {/* PTM */}
        <div>
          <label className="block text-[10px] font-semibold tracking-[2px] text-purple mb-1.5">
            PRIMARY TARGET MARKET
          </label>
          <input
            type="text"
            value={ptm}
            onChange={(e) => onChange("ptm", e.target.value)}
            disabled={isRunning}
            placeholder="e.g. Medanese Upper Middle Class, 25-45"
            className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-sm text-text-primary placeholder-text-dim focus:outline-none focus:border-purple focus:ring-1 focus:ring-purple/40 disabled:opacity-50"
          />
        </div>

        {/* STM */}
        <div>
          <label className="block text-[10px] font-semibold tracking-[2px] text-amber mb-1.5">
            SECONDARY TARGET MARKET
          </label>
          <input
            type="text"
            value={stm}
            onChange={(e) => onChange("stm", e.target.value)}
            disabled={isRunning}
            placeholder="Optional — leave blank"
            className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-sm text-text-primary placeholder-text-dim focus:outline-none focus:border-amber focus:ring-1 focus:ring-amber/40 disabled:opacity-50"
          />
        </div>

        {/* Pills */}
        <div className="space-y-1 text-[11px] text-text-dim">
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded bg-purple/15 text-purple border border-purple/30 font-semibold">PTM</span>
            <span className="truncate">{ptm || "—"}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded bg-amber/15 text-amber border border-amber/30 font-semibold">STM</span>
            <span className="truncate">{stm || "(none)"}</span>
          </div>
        </div>

        {/* Agent Limit Slider */}
        <div>
          <div className="flex justify-between items-center mb-1.5">
            <label className="text-[10px] font-semibold tracking-[2px] text-text-dim uppercase">
              Agents to Simulate
            </label>
            <span className="text-sm font-bold text-purple">{agentLimit}</span>
          </div>
          <input
            type="range"
            min={5}
            max={100}
            step={5}
            value={agentLimit}
            onChange={(e) => onChange("agentLimit", Number(e.target.value))}
            disabled={isRunning}
            className="w-full accent-purple disabled:opacity-50"
          />
          <div className="flex justify-between text-[10px] text-text-dim mt-0.5">
            <span>5</span><span>100</span>
          </div>
        </div>

        {/* Group Size Slider */}
        <div>
          <div className="flex justify-between items-center mb-1.5">
            <label className="text-[10px] font-semibold tracking-[2px] text-text-dim uppercase">
              Breakout Room Size
            </label>
            <span className="text-sm font-bold text-purple">{groupSize}</span>
          </div>
          <input
            type="range"
            min={3}
            max={10}
            step={1}
            value={groupSize}
            onChange={(e) => onChange("groupSize", Number(e.target.value))}
            disabled={isRunning}
            className="w-full accent-purple disabled:opacity-50"
          />
          <div className="flex justify-between text-[10px] text-text-dim mt-0.5">
            <span>3</span><span>10</span>
          </div>
        </div>

        {/* Runtime estimate */}
        <div className="border-t border-border pt-4">
          <h3 className="text-xs font-bold tracking-[2px] text-text-dim uppercase mb-2">
            📊 Est. Runtime
          </h3>
          <div className="bg-bg border border-border rounded-lg p-3 text-[12px] text-text-muted">
            ~{estMin} min for {agentLimit} agents, {nGroups} breakout {nGroups === 1 ? "room" : "rooms"}
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="px-5 py-4 border-t border-border">
        <p className="text-[10px] text-text-dim text-center">
          PANTHEON v1.0 · Powered by Anthropic Claude + Modal
        </p>
      </div>
    </aside>
  );
}
