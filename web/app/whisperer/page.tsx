"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";

// ── Types ─────────────────────────────────────────────────────────────────────

interface WhisperResult {
  prospect_name?: string;
  simulated_life?: string;
  plain_language_brief?: string;
  section_0_quick_brief?: {
    engagement_hook_card?: { hook: string; stay: string; close: string };
    key_talking_points?: Array<{
      point: string;
      why_it_lands: string;
      example_phrasing: string;
      genome_driver: string;
    }>;
  };
  section_1_human_snapshot?: {
    what_they_actually_need?: string;
    pride_point?: string;
    one_thing_to_remember?: string;
    what_makes_them_trust?: string;
    what_makes_them_shut_down?: string;
  };
  section_2_conversation_architecture?: {
    stage_1_arrive?: { purpose: string; content: string };
    stage_5_reframe?: { purpose: string; content: string };
    stage_7_cta?: { purpose: string; content: string };
  };
  section_3_signal_reading?: {
    open_signals?: string[];
    close_signals?: string[];
  };
  section_5_product_fit?: {
    fit_status?: string;
    fit_rationale?: string;
    pain_it_addresses?: string;
    how_to_introduce_it?: string;
    honest_limitation?: string;
  };
  section_6_post_conversation?: { within_24_hours?: string };
  error?: string;
}

interface HistoryEntry {
  id: string;
  timestamp: string;
  prospect_name: string;
  linkedin_url: string;
  instagram_url: string;
  product_details: string;
  result: WhisperResult;
}

const FIT_COLORS: Record<string, { bg: string; border: string; text: string; label: string }> = {
  TRUE_FIT:    { bg: "bg-green/15",         border: "border-green/30",          text: "text-green",       label: "🟢 TRUE FIT"    },
  PARTIAL_FIT: { bg: "bg-amber/15",         border: "border-amber/30",          text: "text-amber",       label: "🟡 PARTIAL FIT" },
  NO_FIT:      { bg: "bg-red-500/15",       border: "border-red-500/30",        text: "text-red-400",     label: "🔴 NO FIT"      },
  VERIFY_FIT:  { bg: "bg-blue-500/15",      border: "border-blue-500/30",       text: "text-blue-400",    label: "🔵 VERIFY FIT"  },
};

// ── Output Renderer ───────────────────────────────────────────────────────────

function WhisperOutput({ result, linkedinUrl, instagramUrl }: { result: WhisperResult; linkedinUrl: string; instagramUrl: string }) {
  const [openTp, setOpenTp] = useState<number | null>(null);
  const [showRaw, setShowRaw] = useState(false);

  const name = result.prospect_name || "Unknown";
  const simLife = result.simulated_life || "";

  // Extract region & background from simulated_life
  let region = "Unknown Region";
  let background = "Professional";
  for (const line of simLife.split("\n")) {
    if (line.includes("Region:"))     region     = line.split("Region:")[1].trim();
    if (line.startsWith("Background:")) background = line.split("Background:")[1].trim();
  }
  const initials = name.split(" ").filter(Boolean).slice(0, 2).map(w => w[0].toUpperCase()).join("");

  const snap  = result.section_1_human_snapshot         || {};
  const arch  = result.section_2_conversation_architecture || {};
  const sig   = result.section_3_signal_reading          || {};
  const pf    = result.section_5_product_fit             || {};
  const qb    = result.section_0_quick_brief             || {};
  const hookCard   = qb.engagement_hook_card    || { hook: "", stay: "", close: "" };
  const talkPoints = qb.key_talking_points      || [];

  const fitStatus  = pf.fit_status || "VERIFY_FIT";
  const fitColors  = FIT_COLORS[fitStatus] || FIT_COLORS.VERIFY_FIT;
  const fitRationale = pf.fit_rationale || pf.pain_it_addresses || "";

  const hook1 = (sig.open_signals?.[0]) || snap.what_they_actually_need || "Efisiensi dan menghemat waktu.";
  const hook2 = (sig.open_signals?.[1]) || snap.pride_point             || "Pencapaian profesional.";
  const hook3 = snap.one_thing_to_remember || "Jangan terlalu memaksakan penjualan.";

  const win1  = pf.how_to_introduce_it          || "Bingkasi sesuai dengan tujuan inti mereka.";
  const win2  = snap.what_makes_them_trust       || "Angka langsung, tanpa kerumitan.";
  const win3  = pf.pain_it_addresses             || "Menyelesaikan inefisiensi.";
  const lose1 = snap.what_makes_them_shut_down   || "Bukti sosial, taktik tekanan tinggi.";
  const lose2 = pf.honest_limitation             || "Berjanji berlebihan pada ruang lingkup.";
  const lose3 = sig.close_signals?.[0]           || "Mengabaikan batasan mereka.";

  const stages: Array<{ title: string; data: { purpose: string; content: string } | undefined }> = [
    { title: "Pembukaan & Cek",           data: arch.stage_1_arrive  },
    { title: "Mengubah Sudut Pandang",    data: arch.stage_5_reframe },
    { title: "Penutupan Rendah Gesekan",  data: arch.stage_7_cta    },
  ];

  return (
    <div className="animate-fadeIn space-y-5">
      {/* Breadcrumb */}
      <div className="text-xs text-text-dim font-mono">
        WHISPR / PIPELINE / <span className="text-text-muted">{name.toUpperCase()}</span>
      </div>

      {/* Top grid: Identity + Intel */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

        {/* Identity Card */}
        <div className="bg-[#0f172a] border border-[#1e293b] rounded-xl p-5 relative overflow-hidden">
          <div className="absolute top-0 left-0 w-1 h-full bg-indigo-500" />
          <div className="flex justify-between items-start">
            <div>
              <div className="text-xl font-bold text-white mb-0.5">{name}</div>
              <div className="text-xs text-[#94a3b8]">💼 {background.slice(0, 60)}{background.length > 60 ? "…" : ""}</div>
              <div className="text-xs text-[#94a3b8] mt-0.5">📍 {region}</div>
            </div>
            <div className="w-12 h-12 rounded-full bg-[#1e293b] border border-[#334155] flex items-center justify-center text-indigo-400 font-bold text-lg shrink-0">
              {initials}
            </div>
          </div>
          <div className={`mt-4 rounded-lg p-3 ${fitColors.bg} border ${fitColors.border}`}>
            <div className={`text-xs font-bold mb-1 ${fitColors.text}`}>🚩 OBJECTIVE: {fitStatus.replace("_", " ")}</div>
            <div className="text-xs text-[#fde68a]/70 leading-relaxed">{fitRationale}</div>
          </div>
        </div>

        {/* Visual Intel Hooks */}
        <div className="bg-[#0f172a] border border-[#1e293b] rounded-xl p-5">
          <div className="text-[10px] font-bold tracking-widest text-[#64748b] uppercase mb-4">🎯 Visual Intel (Hooks)</div>
          {[
            { icon: "🎯", bg: "bg-emerald-500/10 text-emerald-400", title: "Dorongan Utama",   text: hook1 },
            { icon: "⭐", bg: "bg-blue-500/10 text-blue-400",         title: "Titik Kebanggaan", text: hook2 },
            { icon: "⚡", bg: "bg-purple/10 text-purple",             title: "Aturan Utama",    text: hook3 },
          ].map((h) => (
            <div key={h.title} className="flex items-start gap-3 mb-3 last:mb-0">
              <div className={`w-7 h-7 rounded flex items-center justify-center text-sm shrink-0 ${h.bg}`}>{h.icon}</div>
              <div>
                <div className="text-xs font-semibold text-[#e2e8f0]">{h.title}</div>
                <div className="text-xs text-[#94a3b8] mt-0.5 leading-relaxed">{h.text}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Win/Lose Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-[#0f172a] border border-emerald-900/50 rounded-xl p-5">
          <div className="text-sm font-bold text-emerald-400 mb-3">✔️ CARA MEMENANGKAN MEREKA</div>
          <ul className="space-y-2 text-sm text-[#cbd5e1]">
            {[win1, win2, win3].map((w, i) => (
              <li key={i} className="flex items-start gap-2"><span className="text-emerald-500 mt-0.5">✓</span>{w}</li>
            ))}
          </ul>
        </div>
        <div className="bg-[#0f172a] border border-rose-900/50 rounded-xl p-5">
          <div className="text-sm font-bold text-rose-400 mb-3">✖️ CARA KEHILANGAN MEREKA</div>
          <ul className="space-y-2 text-sm text-[#cbd5e1]">
            {[lose1, lose2, lose3].map((l, i) => (
              <li key={i} className="flex items-start gap-2"><span className="text-rose-500 mt-0.5">✗</span>{l}</li>
            ))}
          </ul>
        </div>
      </div>

      {/* Meeting Blueprint */}
      <div className="bg-[#0f172a] border border-[#1e293b] rounded-xl overflow-hidden">
        <div className="bg-[#1e293b]/50 px-5 py-3 text-xs font-bold tracking-widest text-[#cbd5e1] uppercase">
          📋 Panduan Client — Meeting Blueprint
        </div>
        {stages.map(({ title, data }, i) => data ? (
          <div key={i} className="flex items-start gap-4 px-5 py-4 border-b border-[#1e293b]/50 last:border-0 hover:bg-[#1e293b]/20 transition-colors">
            <div className="w-8 h-8 rounded-full bg-indigo-500/20 text-indigo-400 flex items-center justify-center font-bold text-sm shrink-0">
              {i + 1}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-bold text-[#e2e8f0] mb-0.5">{title}</div>
              <div className="text-xs text-[#94a3b8] mb-2">{data.purpose}</div>
              <div className="text-[10px] font-semibold tracking-widest text-[#475569] uppercase mb-1">
                Contoh kalimat — sesuaikan, jangan dibaca verbatim
              </div>
              <div className="bg-[#020617] border border-[#1e293b] rounded px-3 py-2 text-xs text-indigo-300 italic leading-relaxed">
                💬 {data.content}
              </div>
            </div>
          </div>
        ) : null)}
      </div>

      {/* Quick Brief Hook Card */}
      {(hookCard.hook || hookCard.stay || hookCard.close) && (
        <div>
          <div className="text-[10px] font-bold tracking-widest text-[#64748b] uppercase mb-2">⚡ Kartu Cepat — {name}</div>
          <div className="grid grid-cols-3 gap-3">
            {[
              { label: "🎣 Hook",         text: hookCard.hook,  accent: "border-l-amber",   color: "text-amber"       },
              { label: "🔗 Pertahankan",  text: hookCard.stay,  accent: "border-l-indigo-400", color: "text-indigo-400" },
              { label: "🎯 Close",        text: hookCard.close, accent: "border-l-emerald-400", color: "text-emerald-400" },
            ].map((c) => (
              <div key={c.label} className={`bg-[#0f172a] rounded-xl p-4 border-l-4 ${c.accent}`}>
                <div className={`text-[10px] font-bold uppercase tracking-wider mb-1.5 ${c.color}`}>{c.label}</div>
                <div className="text-xs text-[#cbd5e1] leading-relaxed">{c.text}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Talking Points */}
      {talkPoints.length > 0 && (
        <div>
          <div className="text-[10px] font-bold tracking-widest text-[#64748b] uppercase mb-2">💬 Talking Points Utama</div>
          <div className="space-y-2">
            {talkPoints.map((tp, i) => (
              <div key={i} className="bg-[#0f172a] border border-[#1e293b] rounded-xl overflow-hidden">
                <button
                  onClick={() => setOpenTp(openTp === i ? null : i)}
                  className="w-full flex items-center justify-between px-4 py-3 text-left text-sm font-semibold text-[#e2e8f0] hover:bg-[#1e293b]/30 transition-colors"
                >
                  <span>💡 Talking Point {i + 1}</span>
                  <span className="text-[#64748b]">{openTp === i ? "▲" : "▼"}</span>
                </button>
                {openTp === i && (
                  <div className="px-4 pb-4 space-y-2 animate-fadeIn">
                    <p className="text-sm font-bold text-[#e2e8f0] leading-snug">{tp.point}</p>
                    {tp.genome_driver && (
                      <span className="inline-block text-[10px] font-semibold px-2 py-0.5 rounded-full bg-indigo-500/15 text-indigo-300">🧬 {tp.genome_driver}</span>
                    )}
                    {tp.why_it_lands && (
                      <p className="text-xs text-[#94a3b8] leading-relaxed"><strong className="text-[#cbd5e1]">Mengapa efektif:</strong> {tp.why_it_lands}</p>
                    )}
                    {tp.example_phrasing && (
                      <div>
                        <div className="text-[10px] font-semibold tracking-widest text-[#475569] uppercase mb-1">Contoh kalimat</div>
                        <div className="bg-[#020617] border-l-2 border-[#334155] rounded px-3 py-2 text-xs text-indigo-300 italic leading-relaxed">"{tp.example_phrasing}"</div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Raw data collapsible */}
      <div>
        <button
          onClick={() => setShowRaw(v => !v)}
          className="flex items-center gap-2 text-xs font-semibold text-[#64748b] hover:text-[#94a3b8] transition-colors"
        >
          <span>{showRaw ? "▾" : "▸"}</span> Lihat Data Psikologis Mentah
        </button>
        {showRaw && (
          <div className="mt-3 bg-bg border border-border rounded-xl p-4 space-y-3 animate-fadeIn">
            {result.plain_language_brief && (
              <div>
                <div className="text-xs font-bold text-text-dim uppercase tracking-widest mb-1">Ringkasan Bahasa Sederhana</div>
                <p className="text-xs text-text-muted leading-relaxed">{result.plain_language_brief}</p>
              </div>
            )}
            {result.section_6_post_conversation?.within_24_hours && (
              <div>
                <div className="text-xs font-bold text-text-dim uppercase tracking-widest mb-1">Pasca Pertemuan (24 jam)</div>
                <p className="text-xs text-text-muted leading-relaxed">{result.section_6_post_conversation.within_24_hours}</p>
              </div>
            )}
            {simLife && (
              <div>
                <div className="text-xs font-bold text-text-dim uppercase tracking-widest mb-1">PANTHEON Life Blueprint</div>
                <pre className="text-[10px] text-text-dim whitespace-pre-wrap font-mono leading-relaxed">{simLife}</pre>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ── History helpers ───────────────────────────────────────────────────────────

const HISTORY_KEY = "pantheon_whisper_history";

function loadWhisperHistory(): HistoryEntry[] {
  if (typeof window === "undefined") return [];
  try { return JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]"); }
  catch { return []; }
}

function saveWhisperHistory(entries: HistoryEntry[]) {
  localStorage.setItem(HISTORY_KEY, JSON.stringify(entries.slice(0, 30)));
}

// ── Main Page ─────────────────────────────────────────────────────────────────

type RunPhase = "idle" | "running" | "done" | "error";

const STEPS = [
  "Scraping LinkedIn profile",
  "Scraping Instagram profile",
  "Vision analysis on images",
  "Building PANTHEON genome & life blueprint",
  "Generating Human Whisperer conversation prep",
];

export default function WhispererPage() {
  const [tab, setTab] = useState<"new" | "history">("new");

  // Form state
  const [linkedinUrl, setLinkedinUrl]     = useState("");
  const [instagramUrl, setInstagramUrl]   = useState("");
  const [productDetails, setProductDetails] = useState("");

  // Run state
  const [phase, setPhase]         = useState<RunPhase>("idle");
  const [currentStep, setCurrentStep] = useState(0);
  const [elapsed, setElapsed]     = useState(0);
  const [result, setResult]       = useState<WhisperResult | null>(null);
  const [errorMsg, setErrorMsg]   = useState("");

  // History
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [viewingEntry, setViewingEntry] = useState<HistoryEntry | null>(null);

  useEffect(() => { setHistory(loadWhisperHistory()); }, []);

  // Elapsed timer
  useEffect(() => {
    if (phase !== "running") return;
    const t = setInterval(() => setElapsed(s => s + 1), 1000);
    return () => clearInterval(t);
  }, [phase]);

  // Fake step progress based on elapsed time
  useEffect(() => {
    if (phase !== "running") return;
    // Rough time budget per step (s): 20, 15, 10, 40, 60
    const budgets = [20, 15, 10, 40, 60];
    let cursor = 0;
    for (let i = 0; i < budgets.length; i++) {
      cursor += budgets[i];
      if (elapsed < cursor) { setCurrentStep(i); break; }
      if (i === budgets.length - 1) setCurrentStep(i);
    }
  }, [elapsed, phase]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!linkedinUrl || !instagramUrl || !productDetails) return;

    setPhase("running");
    setElapsed(0);
    setCurrentStep(0);
    setResult(null);
    setErrorMsg("");

    try {
      const res = await fetch("/api/human-whisperer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          linkedin_url: linkedinUrl,
          instagram_url: instagramUrl,
          product_details: productDetails,
        }),
      });

      const data: WhisperResult = await res.json();

      if (!res.ok || data.error) {
        throw new Error(data.error || `Error ${res.status}`);
      }

      setResult(data);
      setPhase("done");

      // Save to history
      const entry: HistoryEntry = {
        id: Date.now().toString(),
        timestamp: new Date().toISOString(),
        prospect_name: data.prospect_name || "Unknown",
        linkedin_url: linkedinUrl,
        instagram_url: instagramUrl,
        product_details: productDetails,
        result: data,
      };
      const updated = [entry, ...loadWhisperHistory()];
      saveWhisperHistory(updated);
      setHistory(updated);
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : String(err));
      setPhase("error");
    }
  }

  const elapsedStr = `${Math.floor(elapsed / 60).toString().padStart(2, "0")}:${(elapsed % 60).toString().padStart(2, "0")}`;

  return (
    <div className="flex h-screen overflow-hidden bg-bg">
      {/* Left sidebar */}
      <aside className="w-64 shrink-0 bg-card border-r border-border flex flex-col h-screen">
        <div className="flex flex-col items-center py-7 px-5 border-b border-border">
          <span className="text-4xl mb-2">🧠</span>
          <div className="text-base font-black tracking-[3px] text-white">WHISPERER</div>
          <div className="text-[9px] tracking-[3px] text-text-dim mt-0.5">HUMAN INTELLIGENCE</div>
        </div>
        <div className="flex-1 px-4 py-5 space-y-3">
          <p className="text-[11px] text-text-dim leading-relaxed">
            LinkedIn + Instagram → PANTHEON genome → hyper-targeted conversation prep.
          </p>
          <div className="space-y-1 text-[11px]">
            <div className="text-[10px] font-bold tracking-widest text-text-dim uppercase mb-2">Pipeline</div>
            {STEPS.map((s, i) => (
              <div key={i} className="flex items-center gap-2 text-text-dim">
                <span>{i + 1}.</span><span>{s}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="px-4 py-4 border-t border-border">
          <Link
            href="/"
            className="flex items-center gap-2 text-xs font-semibold text-text-dim hover:text-purple transition-colors"
          >
            ← Back to PANTHEON
          </Link>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-8 py-10">

          {/* Header */}
          <div className="flex items-start justify-between mb-6">
            <div>
              <div className="text-xs font-semibold tracking-[4px] text-amber uppercase mb-2">Client Intelligence</div>
              <h1 className="text-3xl font-black text-white mb-1">Human Whisperer</h1>
              <p className="text-text-dim text-sm">
                Enter a prospect's LinkedIn and Instagram, plus what you're offering.
                The engine builds their full life blueprint and returns a hyper-targeted conversation prep.
              </p>
            </div>
            <Link
              href="/"
              className="shrink-0 flex items-center gap-2 px-4 py-2 rounded-xl border border-purple/40 bg-purple/10 text-purple text-sm font-semibold hover:bg-purple/20 hover:border-purple/60 transition-all duration-200 mt-1"
            >
              <span className="text-purple/60">←</span>
              PANTHEON
              <span>⚡</span>
            </Link>
          </div>

          {/* Tabs */}
          <div className="flex border-b border-border mb-6">
            {(["new", "history"] as const).map((t) => (
              <button
                key={t}
                onClick={() => { setTab(t); setViewingEntry(null); }}
                className={`px-4 py-2 text-sm font-semibold transition-colors ${
                  tab === t ? "text-amber border-b-2 border-amber" : "text-text-dim hover:text-text-muted"
                }`}
              >
                {t === "new" ? "🆕 New Analysis" : `📂 Previous Analyses (${history.length})`}
              </button>
            ))}
          </div>

          {/* ── TAB: New Analysis ── */}
          {tab === "new" && (
            <>
              {/* Form */}
              {phase !== "done" && (
                <form onSubmit={handleSubmit} className="space-y-4 mb-6">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-[10px] font-bold tracking-widest text-text-dim uppercase mb-1.5">
                        LinkedIn Profile URL
                      </label>
                      <input
                        type="url"
                        value={linkedinUrl}
                        onChange={e => setLinkedinUrl(e.target.value)}
                        placeholder="https://linkedin.com/in/username"
                        disabled={phase === "running"}
                        className="w-full bg-card border border-border rounded-lg px-3 py-2 text-sm text-text-primary placeholder-text-dim focus:outline-none focus:border-amber focus:ring-1 focus:ring-amber/30 disabled:opacity-50"
                      />
                    </div>
                    <div>
                      <label className="block text-[10px] font-bold tracking-widest text-text-dim uppercase mb-1.5">
                        Instagram Profile URL
                      </label>
                      <input
                        type="url"
                        value={instagramUrl}
                        onChange={e => setInstagramUrl(e.target.value)}
                        placeholder="https://instagram.com/username"
                        disabled={phase === "running"}
                        className="w-full bg-card border border-border rounded-lg px-3 py-2 text-sm text-text-primary placeholder-text-dim focus:outline-none focus:border-amber focus:ring-1 focus:ring-amber/30 disabled:opacity-50"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-[10px] font-bold tracking-widest text-text-dim uppercase mb-1.5">
                      Product / Service Brief
                    </label>
                    <textarea
                      value={productDetails}
                      onChange={e => setProductDetails(e.target.value)}
                      rows={5}
                      disabled={phase === "running"}
                      placeholder="Describe what you're offering — what it does, who it's for, what it genuinely delivers, and what it cannot do. Honesty here makes the sanity check meaningful."
                      className="w-full bg-card border border-border rounded-lg px-3 py-2.5 text-sm text-text-primary placeholder-text-dim resize-none focus:outline-none focus:border-amber focus:ring-1 focus:ring-amber/30 disabled:opacity-50"
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={!linkedinUrl || !instagramUrl || !productDetails || phase === "running"}
                    className="w-full py-3 rounded-xl font-bold text-sm bg-gradient-to-r from-amber/80 to-amber text-[#0a0a0f] disabled:opacity-40 disabled:cursor-not-allowed hover:opacity-90 transition-opacity"
                  >
                    {phase === "running" ? "Running…" : "🧠 Run Human Whisperer"}
                  </button>
                </form>
              )}

              {/* Progress */}
              {phase === "running" && (
                <div className="bg-card border border-border rounded-2xl p-6 mb-6 animate-fadeIn">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-sm font-bold text-white">⚙️ Pipeline Running</h3>
                    <span className="font-mono text-amber text-sm">{elapsedStr}</span>
                  </div>
                  <div className="space-y-2">
                    {STEPS.map((s, i) => (
                      <div key={i} className={`flex items-center gap-3 text-sm transition-colors ${
                        i < currentStep  ? "text-green" :
                        i === currentStep ? "text-amber" : "text-text-dim"
                      }`}>
                        <span className="w-4 shrink-0">
                          {i < currentStep  ? "✓" :
                           i === currentStep ? <span className="inline-block w-3 h-3 border-2 border-amber border-t-transparent rounded-full animate-spin" /> : "○"}
                        </span>
                        {i === currentStep ? <span className="animate-pulse_slow">{s}…</span> : <span>{s}</span>}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Error */}
              {phase === "error" && (
                <div className="mb-6 p-4 rounded-xl bg-red-900/20 border border-red-500/40 text-red-300 text-sm animate-fadeIn">
                  <strong>Error:</strong> {errorMsg}
                  <button
                    onClick={() => setPhase("idle")}
                    className="ml-4 underline text-xs hover:no-underline"
                  >
                    Try again
                  </button>
                </div>
              )}

              {/* Results */}
              {phase === "done" && result && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-bold text-white">✓ Analysis Complete — {result.prospect_name}</h3>
                    <button
                      onClick={() => { setPhase("idle"); setResult(null); }}
                      className="text-xs text-text-dim hover:text-text-muted border border-border rounded-lg px-3 py-1.5 transition-colors"
                    >
                      + New Analysis
                    </button>
                  </div>
                  <WhisperOutput result={result} linkedinUrl={linkedinUrl} instagramUrl={instagramUrl} />
                </div>
              )}
            </>
          )}

          {/* ── TAB: History ── */}
          {tab === "history" && (
            <>
              {viewingEntry ? (
                <div>
                  <button
                    onClick={() => setViewingEntry(null)}
                    className="flex items-center gap-1 text-xs text-text-dim hover:text-text-muted mb-5 transition-colors"
                  >
                    ← Back to list
                  </button>
                  <WhisperOutput
                    result={viewingEntry.result}
                    linkedinUrl={viewingEntry.linkedin_url}
                    instagramUrl={viewingEntry.instagram_url}
                  />
                </div>
              ) : history.length === 0 ? (
                <div className="text-center py-16">
                  <div className="text-4xl mb-3">📂</div>
                  <p className="text-text-dim text-sm">No previous analyses. Run one in the New Analysis tab.</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {history.map((entry) => {
                    const fitStatus = entry.result.section_5_product_fit?.fit_status || "VERIFY_FIT";
                    const fc = FIT_COLORS[fitStatus] || FIT_COLORS.VERIFY_FIT;
                    return (
                      <div
                        key={entry.id}
                        onClick={() => setViewingEntry(entry)}
                        className="bg-card border border-border rounded-xl p-4 cursor-pointer hover:border-border-hover transition-colors"
                      >
                        <div className="flex items-center justify-between">
                          <div>
                            <span className="text-sm font-semibold text-text-primary">{entry.prospect_name}</span>
                            <p className="text-xs text-text-dim mt-0.5">
                              {new Date(entry.timestamp).toLocaleString()} · {entry.linkedin_url}
                            </p>
                          </div>
                          <span className={`text-xs px-2 py-0.5 rounded border shrink-0 ml-3 ${fc.bg} ${fc.border} ${fc.text}`}>
                            {fc.label}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </>
          )}
        </div>
      </main>
    </div>
  );
}
