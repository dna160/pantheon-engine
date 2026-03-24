"use client";

import React, { useState, useRef } from "react";

interface BriefInputProps {
  value: string;
  onChange: (text: string) => void;
  disabled?: boolean;
}

export default function BriefInput({ value, onChange, disabled }: BriefInputProps) {
  const [activeTab, setActiveTab] = useState<"paste" | "upload">("paste");
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState<{ type: "ok" | "err"; text: string } | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const charCount = value.length;
  const briefReady = charCount > 50;

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setUploadMsg(null);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const res = await fetch("/api/extract", { method: "POST", body: formData });
      const json = await res.json();

      if (res.ok && json.text) {
        onChange(json.text);
        setUploadMsg({ type: "ok", text: `Extracted ${json.text.length.toLocaleString()} chars from ${file.name}` });
      } else {
        setUploadMsg({ type: "err", text: json.error || "Extraction failed" });
      }
    } catch (err) {
      setUploadMsg({ type: "err", text: String(err) });
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  return (
    <div>
      <div className="flex items-center gap-1 mb-3">
        <h2 className="text-lg font-bold text-white">📋 Campaign Brief</h2>
        <span className="text-text-dim text-sm ml-2">
          Paste your brief or upload a document — text will be auto-extracted.
        </span>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-border mb-4">
        {(["paste", "upload"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-sm font-semibold transition-colors ${
              activeTab === tab
                ? "text-purple border-b-2 border-purple"
                : "text-text-dim hover:text-text-muted"
            }`}
          >
            {tab === "paste" ? "✏️  Paste Text" : "📎  Upload File"}
          </button>
        ))}
      </div>

      {activeTab === "paste" && (
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          rows={7}
          placeholder={
            "Describe the creative stimulus, product, audience, and market context.\n\n" +
            "Example: A fintech app displays a Buy-Now-Pay-Later advertisement that lets users split " +
            "rent payments into 4 installments in Indonesia."
          }
          className="w-full bg-card border border-border rounded-xl px-4 py-3 text-sm text-text-primary placeholder-text-dim resize-none focus:outline-none focus:border-purple focus:ring-1 focus:ring-purple/40 disabled:opacity-50 font-sans"
        />
      )}

      {activeTab === "upload" && (
        <div
          className="border-2 border-dashed border-border rounded-xl p-8 text-center hover:border-purple/50 transition-colors cursor-pointer"
          onClick={() => fileRef.current?.click()}
        >
          <input
            ref={fileRef}
            type="file"
            accept=".pdf,.docx,.doc,.txt"
            onChange={handleFileChange}
            className="hidden"
          />
          {uploading ? (
            <div className="flex flex-col items-center gap-2">
              <div className="w-6 h-6 border-2 border-purple border-t-transparent rounded-full animate-spin" />
              <span className="text-text-dim text-sm">Extracting text...</span>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-2">
              <span className="text-3xl">📄</span>
              <p className="text-text-muted text-sm font-medium">
                Click to upload or drag &amp; drop
              </p>
              <p className="text-text-dim text-xs">PDF, DOCX, DOC, TXT</p>
            </div>
          )}
          {uploadMsg && (
            <div
              className={`mt-3 text-xs font-medium px-3 py-2 rounded-lg ${
                uploadMsg.type === "ok"
                  ? "bg-green/15 text-green border border-green/30"
                  : "bg-red-500/15 text-red-400 border border-red-500/30"
              }`}
            >
              {uploadMsg.text}
            </div>
          )}
        </div>
      )}

      {/* Character count + status */}
      <div className="flex items-center justify-between mt-2 px-1">
        <span className="text-xs text-text-dim">{charCount.toLocaleString()} characters</span>
        {briefReady ? (
          <span className="text-xs font-semibold px-2.5 py-0.5 rounded bg-green/15 text-green border border-green/30">
            ✓ Brief ready
          </span>
        ) : (
          <span className="text-xs text-text-dim">Awaiting brief…</span>
        )}
      </div>
    </div>
  );
}
