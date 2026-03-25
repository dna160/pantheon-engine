"use client";

import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface ResultsPanelProps {
  report: string;
  elapsed: number;
  client: string;
  target: string;
  brief?: string;
}

export default function ResultsPanel({ report, elapsed, client, target, brief = "" }: ResultsPanelProps) {
  const [copied, setCopied] = useState(false);
  const [downloadingDocx, setDownloadingDocx] = useState(false);
  const [downloadingPptx, setDownloadingPptx] = useState(false);
  const [downloadingWhisperer, setDownloadingWhisperer] = useState(false);

  const elapsedStr = elapsed >= 60
    ? `${Math.floor(elapsed / 60)}m ${elapsed % 60}s`
    : `${elapsed}s`;

  const slug = (client || target).replace(/[^\w]/g, "_").slice(0, 40);

  function handleCopy() {
    navigator.clipboard.writeText(report);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  function handleDownloadMd() {
    const blob = new Blob([report], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `PANTHEON_Report_${slug}.md`;
    a.click();
    URL.revokeObjectURL(url);
  }

  async function handleDownloadDocx() {
    setDownloadingDocx(true);
    try {
      const res = await fetch("/api/download/docx", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ report, target, client, brief }),
      });
      if (!res.ok) throw new Error(await res.text());
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `PANTHEON_Report_${slug}.docx`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      alert("Failed to generate Word document: " + (e instanceof Error ? e.message : e));
    } finally {
      setDownloadingDocx(false);
    }
  }

  async function handleDownloadWhisperer() {
    setDownloadingWhisperer(true);
    try {
      const res = await fetch("/api/download/whisperer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ report, target, client, brief }),
      });
      if (!res.ok) throw new Error(await res.text());
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `PANTHEON_ClientWhisperer_${slug}.docx`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      alert("Failed to generate Client Whisperer doc: " + (e instanceof Error ? e.message : e));
    } finally {
      setDownloadingWhisperer(false);
    }
  }

  async function handleDownloadPptx() {
    setDownloadingPptx(true);
    try {
      const res = await fetch("/api/download/pptx", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ report, target, client, brief }),
      });
      if (!res.ok) throw new Error(await res.text());
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `PANTHEON_Report_${slug}.pptx`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      alert("Failed to generate PowerPoint: " + (e instanceof Error ? e.message : e));
    } finally {
      setDownloadingPptx(false);
    }
  }

  return (
    <div className="animate-fadeIn">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="text-lg font-bold text-white flex items-center gap-2">
            <span className="text-green">✓</span> PANTHEON Report
          </h3>
          <p className="text-xs text-text-dim mt-0.5">
            {client && <span className="text-text-muted font-semibold">{client} · </span>}
            {target} · Completed in {elapsedStr}
          </p>
        </div>
        <div className="flex flex-wrap gap-2 justify-end">
          <button
            onClick={handleCopy}
            className="px-3 py-1.5 text-xs font-semibold rounded-lg border border-border text-text-muted hover:border-purple hover:text-purple transition-colors"
          >
            {copied ? "✓ Copied" : "Copy MD"}
          </button>
          <button
            onClick={handleDownloadMd}
            className="px-3 py-1.5 text-xs font-semibold rounded-lg border border-border text-text-muted hover:border-green hover:text-green transition-colors"
          >
            ↓ .md
          </button>
          <button
            onClick={handleDownloadDocx}
            disabled={downloadingDocx}
            className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-blue-500/15 border border-blue-500/30 text-blue-400 hover:bg-blue-500/25 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {downloadingDocx ? (
              <span className="flex items-center gap-1">
                <span className="w-3 h-3 border border-blue-400 border-t-transparent rounded-full animate-spin" />
                Building…
              </span>
            ) : "↓ Word .docx"}
          </button>
          <button
            onClick={handleDownloadPptx}
            disabled={downloadingPptx}
            className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-orange-500/15 border border-orange-500/30 text-orange-400 hover:bg-orange-500/25 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {downloadingPptx ? (
              <span className="flex items-center gap-1">
                <span className="w-3 h-3 border border-orange-400 border-t-transparent rounded-full animate-spin" />
                Building…
              </span>
            ) : "↓ Slides .pptx"}
          </button>
          <button
            onClick={handleDownloadWhisperer}
            disabled={downloadingWhisperer}
            className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-amber-500/15 border border-amber-500/30 text-amber-400 hover:bg-amber-500/25 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {downloadingWhisperer ? (
              <span className="flex items-center gap-1">
                <span className="w-3 h-3 border border-amber-400 border-t-transparent rounded-full animate-spin" />
                Building…
              </span>
            ) : "↓ Whisperer .docx"}
          </button>
        </div>
      </div>

      {/* Separator */}
      <div className="h-px bg-border mb-5" />

      {/* Rendered markdown */}
      <div className="prose prose-invert prose-sm max-w-none
        prose-headings:text-white prose-headings:font-bold
        prose-h1:text-2xl prose-h1:tracking-tight
        prose-h2:text-lg prose-h2:text-purple prose-h2:mt-8 prose-h2:mb-3
        prose-h3:text-base prose-h3:text-text-primary
        prose-p:text-text-muted prose-p:leading-relaxed
        prose-li:text-text-muted
        prose-strong:text-white
        prose-em:text-text-muted
        prose-blockquote:border-l-purple prose-blockquote:text-text-dim prose-blockquote:bg-purple/5 prose-blockquote:rounded-r-lg prose-blockquote:py-1
        prose-code:text-purple prose-code:bg-purple/10 prose-code:rounded prose-code:px-1 prose-code:text-[0.8em]
        prose-pre:bg-card prose-pre:border prose-pre:border-border prose-pre:rounded-xl
        prose-table:border-collapse
        prose-th:border prose-th:border-border prose-th:bg-card prose-th:text-text-primary prose-th:px-4 prose-th:py-2
        prose-td:border prose-td:border-border prose-td:text-text-muted prose-td:px-4 prose-td:py-2
        prose-hr:border-border
        prose-a:text-purple prose-a:no-underline hover:prose-a:underline
      ">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{report}</ReactMarkdown>
      </div>
    </div>
  );
}
