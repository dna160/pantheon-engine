"use client";

import React, { useState, useRef } from "react";

interface BriefInputProps {
  value: string;
  onChange: (text: string) => void;
  onImagesExtracted?: (images: string[]) => void;
  disabled?: boolean;
}

export default function BriefInput({ value, onChange, onImagesExtracted, disabled }: BriefInputProps) {
  const [activeTab, setActiveTab] = useState<"paste" | "upload">("paste");
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState<{ type: "ok" | "err"; text: string } | null>(null);
  const [slideCount, setSlideCount] = useState(0);
  const [thumbnails, setThumbnails] = useState<string[]>([]);
  const fileRef = useRef<HTMLInputElement>(null);

  const charCount = value.length;
  const briefReady = charCount > 50;
  const isVisualBrief = (file: File) =>
    file.name.toLowerCase().endsWith(".pdf") || file.name.toLowerCase().endsWith(".pptx");

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setUploadMsg(null);
    setSlideCount(0);
    setThumbnails([]);
    onImagesExtracted?.([]);

    try {
      const formData = new FormData();
      formData.append("file", file);

      if (isVisualBrief(file)) {
        // Multimodal extraction — get both text and slide images from Modal
        const res = await fetch("/api/extract-visual", { method: "POST", body: formData });
        const json = await res.json();

        if (res.ok && json.text) {
          onChange(json.text);
          const imgs: string[] = json.images ?? [];
          setSlideCount(json.slide_count ?? imgs.length);
          setThumbnails(imgs.slice(0, 3));
          onImagesExtracted?.(imgs);
          setUploadMsg({
            type: "ok",
            text: `Extracted ${json.text.length.toLocaleString()} chars + ${imgs.length} slide image${imgs.length !== 1 ? "s" : ""} from ${file.name}`,
          });
        } else {
          setUploadMsg({ type: "err", text: json.error || "Extraction failed" });
        }
      } else {
        // Text-only extraction (DOCX, TXT)
        const res = await fetch("/api/extract", { method: "POST", body: formData });
        const json = await res.json();

        if (res.ok && json.text) {
          onChange(json.text);
          setUploadMsg({ type: "ok", text: `Extracted ${json.text.length.toLocaleString()} chars from ${file.name}` });
        } else {
          setUploadMsg({ type: "err", text: json.error || "Extraction failed" });
        }
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
        <div>
          <div
            className="border-2 border-dashed border-border rounded-xl p-8 text-center hover:border-purple/50 transition-colors cursor-pointer"
            onClick={() => fileRef.current?.click()}
          >
            <input
              ref={fileRef}
              type="file"
              accept=".pdf,.pptx,.docx,.doc,.txt"
              onChange={handleFileChange}
              className="hidden"
            />
            {uploading ? (
              <div className="flex flex-col items-center gap-2">
                <div className="w-6 h-6 border-2 border-purple border-t-transparent rounded-full animate-spin" />
                <span className="text-text-dim text-sm">Extracting slides & text…</span>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-2">
                <span className="text-3xl">📄</span>
                <p className="text-text-muted text-sm font-medium">
                  Click to upload or drag &amp; drop
                </p>
                <p className="text-text-dim text-xs">
                  PDF, PPTX <span className="text-purple font-semibold">→ visuals extracted</span> · DOCX, TXT
                </p>
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

          {/* Slide thumbnails */}
          {thumbnails.length > 0 && (
            <div className="mt-3">
              <p className="text-xs text-text-dim mb-2 font-medium">
                👁 {slideCount} slide{slideCount !== 1 ? "s" : ""} extracted — agents will see these visuals
              </p>
              <div className="flex gap-2 overflow-x-auto pb-1">
                {thumbnails.map((b64, i) => (
                  <img
                    key={i}
                    src={`data:image/jpeg;base64,${b64}`}
                    alt={`Slide ${i + 1}`}
                    className="h-20 rounded-lg border border-purple/30 shrink-0 object-cover"
                  />
                ))}
                {slideCount > 3 && (
                  <div className="h-20 w-16 rounded-lg border border-border bg-card flex items-center justify-center shrink-0">
                    <span className="text-xs text-text-dim font-semibold">+{slideCount - 3}</span>
                  </div>
                )}
              </div>
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
