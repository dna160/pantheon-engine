"use client";

import React from "react";
import Link from "next/link";

export default function WhispererPage() {
  return (
    <div className="flex h-screen items-center justify-center bg-bg">
      <div className="text-center max-w-md px-8">
        <div className="text-5xl mb-4">🧠</div>
        <div className="text-xs font-semibold tracking-[4px] text-amber uppercase mb-2">
          Client Intelligence
        </div>
        <h1 className="text-3xl font-black text-white mb-3">Human Whisperer</h1>
        <p className="text-text-dim text-sm mb-8 leading-relaxed">
          Transform PANTHEON research reports and client profiles into a structured
          conversation prep document for any human engagement.
        </p>
        <div className="bg-card border border-border rounded-xl p-5 mb-8 text-left space-y-2">
          <p className="text-xs font-semibold tracking-widest text-text-dim uppercase">Coming Soon</p>
          <p className="text-text-muted text-sm">
            The Human Whisperer web interface is being built. In the meantime,
            run it locally via the Streamlit dashboard on port 8503.
          </p>
        </div>
        <Link
          href="/"
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl border border-purple/40 bg-purple/10 text-purple text-sm font-semibold hover:bg-purple/20 transition-colors"
        >
          ← Back to PANTHEON
        </Link>
      </div>
    </div>
  );
}
