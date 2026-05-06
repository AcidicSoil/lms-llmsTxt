import type { SearchResult } from "@/lib/search/types";

const BLOCKED_URL_PATTERNS = [
  "youtube.com",
  "twitter.com",
  "x.com",
  "reddit.com",
  ".pdf",
];

export function toSearchQuery(topic: string): string {
  return `${topic} knowledge framework principles theory guide`;
}

export function parseMaxResults(raw: string | undefined, fallback = 8): number {
  const parsed = Number.parseInt(raw ?? String(fallback), 10);
  if (Number.isNaN(parsed)) return fallback;
  return Math.max(1, Math.min(parsed, 20));
}

function canonicalizeUrl(input: string): string | null {
  try {
    const url = new URL(input.trim());
    url.hash = "";
    const normalized = url.toString();
    if (normalized.endsWith("/")) return normalized.slice(0, -1);
    return normalized;
  } catch {
    return null;
  }
}

export function normalizeResults(
  results: SearchResult[],
  maxResults: number
): string[] {
  const seen = new Set<string>();
  const selected: string[] = [];

  for (const result of results) {
    const normalized = canonicalizeUrl(result.url);
    if (!normalized) continue;

    const lower = normalized.toLowerCase();
    if (BLOCKED_URL_PATTERNS.some((pattern) => lower.includes(pattern))) {
      continue;
    }

    if (seen.has(lower)) continue;
    seen.add(lower);
    selected.push(normalized);

    if (selected.length >= maxResults) break;
  }

  return selected;
}
