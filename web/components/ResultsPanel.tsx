"use client";

import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface ResultsPanelProps {
  report: string;
  elapsed: number;
  client: string;
  target: string;
}

export default function ResultsPanel({ report, elapsed, client, target }: ResultsPanelProps) {
  const [copied, setCopied] = useState(false);

  const elapsedStr = elapsed >= 60
    ? `${Math.floor(elapsed / 60)}m ${elapsed % 60}s`
    : `${elapsed}s`;

  function handleCopy() {
    navigator.clipboard.writeText(report);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  function handleDownload() {
    const blob = new Blob([report], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    const slug = (client || target).replace(/[^\w]/g, "_").slice(0, 40);
    a.href = url;
    a.download = `PANTHEON_Report_${slug}_${Date.now()}.md`;
    a.click();
    URL.revokeObjectURL(url);
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
        <div className="flex gap-2">
          <button
            onClick={handleCopy}
            className="px-3 py-1.5 text-xs font-semibold rounded-lg border border-border text-text-muted hover:border-purple hover:text-purple transition-colors"
          >
            {copied ? "✓ Copied" : "Copy MD"}
          </button>
          <button
            onClick={handleDownload}
            className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-green/15 border border-green/30 text-green hover:bg-green/25 transition-colors"
          >
            ↓ Download .md
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
