import type { CampaignEntry } from "./types";

const KEY = "pantheon_campaign_history";

export function loadHistory(): CampaignEntry[] {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(localStorage.getItem(KEY) || "[]");
  } catch {
    return [];
  }
}

export function appendHistory(entry: CampaignEntry): void {
  const entries = loadHistory();
  entries.unshift(entry);
  // Keep last 50 entries
  localStorage.setItem(KEY, JSON.stringify(entries.slice(0, 50)));
}
