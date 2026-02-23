import Hyperbrowser from "@hyperbrowser/sdk";

let client: Hyperbrowser | null = null;

function getClient(): Hyperbrowser {
  if (!client) {
    const apiKey = process.env.HYPERBROWSER_API_KEY;
    if (!apiKey) throw new Error("HYPERBROWSER_API_KEY is not set");
    client = new Hyperbrowser({ apiKey });
  }
  return client;
}

const MAX_CONCURRENCY = Math.max(
  1,
  parseInt(process.env.HYPERBROWSER_MAX_CONCURRENCY ?? "1", 10)
);

/** Identify errors caused by exceeding the plan's concurrency limit. */
function isConcurrencyError(err: unknown): boolean {
  const msg =
    err instanceof Error
      ? err.message.toLowerCase()
      : String(err).toLowerCase();
  return (
    msg.includes("concurrent") ||
    msg.includes("concurrency") ||
    msg.includes("session limit") ||
    msg.includes("too many") ||
    msg.includes("rate limit") ||
    msg.includes("upgrade") ||
    msg.includes("plan")
  );
}

export class ConcurrencyPlanError extends Error {
  constructor() {
    super(
      "Your Hyperbrowser plan only supports 1 concurrent browser. " +
        "The app is running in sequential mode, but multiple scrapes still " +
        "exceeded the limit. Upgrade at https://hyperbrowser.ai to unlock " +
        "parallel execution."
    );
    this.name = "ConcurrencyPlanError";
  }
}

interface ScrapeResult {
  url: string;
  markdown: string;
}

/** Scrape a single URL, re-throwing concurrency errors as ConcurrencyPlanError. */
async function scrapeOne(
  hb: Hyperbrowser,
  url: string
): Promise<ScrapeResult> {
  try {
    const result = await hb.scrape.startAndWait({
      url,
      scrapeOptions: { formats: ["markdown"], onlyMainContent: true },
    });
    return { url, markdown: result.data?.markdown ?? "" };
  } catch (err) {
    if (isConcurrencyError(err)) throw new ConcurrencyPlanError();
    throw err;
  }
}

/**
 * Scrape an array of URLs with bounded concurrency.
 * Defaults to MAX_CONCURRENCY=1 (safe for free-plan users).
 * Set HYPERBROWSER_MAX_CONCURRENCY env var to increase for paid plans.
 */
export async function scrapeUrls(urls: string[]): Promise<ScrapeResult[]> {
  const hb = getClient();

  if (MAX_CONCURRENCY === 1) {
    // Sequential — guaranteed safe on the free plan.
    const results: ScrapeResult[] = [];
    for (const url of urls) {
      try {
        const r = await scrapeOne(hb, url);
        if (r.markdown.length >= 100) results.push(r);
      } catch (err) {
        if (err instanceof ConcurrencyPlanError) throw err;
        console.warn(`[hyperbrowser] Failed to scrape ${url}:`, err);
      }
    }
    return results;
  }

  // Parallel with a concurrency cap (paid plans).
  const queue = [...urls];
  const results: ScrapeResult[] = [];
  const errors: unknown[] = [];

  async function worker() {
    while (queue.length > 0) {
      const url = queue.shift();
      if (!url) break;
      try {
        const r = await scrapeOne(hb, url);
        if (r.markdown.length >= 100) results.push(r);
      } catch (err) {
        if (err instanceof ConcurrencyPlanError) throw err;
        errors.push(err);
        console.warn(`[hyperbrowser] Failed to scrape ${url}:`, err);
      }
    }
  }

  await Promise.all(
    Array.from({ length: MAX_CONCURRENCY }, () => worker())
  );

  if (errors.length > 0 && results.length === 0) {
    console.error("[hyperbrowser] All scrapes failed:", errors);
  }

  return results;
}
