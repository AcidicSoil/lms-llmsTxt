import Hyperbrowser from "@hyperbrowser/sdk";
import { logger } from "@/lib/logging/logger";

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
export async function scrapeUrls(
  urls: string[],
  options?: { requestId?: string }
): Promise<ScrapeResult[]> {
  const startedAt = Date.now();
  const hb = getClient();

  if (MAX_CONCURRENCY === 1) {
    // Sequential — guaranteed safe on the free plan.
    const results: ScrapeResult[] = [];
    for (let index = 0; index < urls.length; index += 1) {
      const url = urls[index];
      try {
        const r = await scrapeOne(hb, url);
        if (r.markdown.length >= 100) {
          results.push(r);
          logger.info({
            event: "scrape.url.succeeded",
            requestId: options?.requestId,
            urlHost: safeHost(url),
            index,
          });
        }
      } catch (err) {
        if (err instanceof ConcurrencyPlanError) throw err;
        logger.warn({
          event: "scrape.url.failed",
          requestId: options?.requestId,
          provider: "hyperbrowser",
          urlHost: safeHost(url),
          index,
          error: err instanceof Error ? { name: err.name, message: err.message } : "unknown_error",
        });
      }
    }
    logger.info({
      event: "scrape.batch.completed",
      requestId: options?.requestId,
      concurrency: MAX_CONCURRENCY,
      requestedUrlCount: urls.length,
      successfulDocCount: results.length,
      failedCount: urls.length - results.length,
      durationMs: Date.now() - startedAt,
    });
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
        if (r.markdown.length >= 100) {
          results.push(r);
          logger.info({
            event: "scrape.url.succeeded",
            requestId: options?.requestId,
            urlHost: safeHost(url),
          });
        }
      } catch (err) {
        if (err instanceof ConcurrencyPlanError) throw err;
        errors.push(err);
        logger.warn({
          event: "scrape.url.failed",
          requestId: options?.requestId,
          provider: "hyperbrowser",
          urlHost: safeHost(url),
          error: err instanceof Error ? { name: err.name, message: err.message } : "unknown_error",
        });
      }
    }
  }

  await Promise.all(
    Array.from({ length: MAX_CONCURRENCY }, () => worker())
  );

  if (errors.length > 0 && results.length === 0) {
    logger.error({
      event: "scrape.batch.completed",
      requestId: options?.requestId,
      concurrency: MAX_CONCURRENCY,
      requestedUrlCount: urls.length,
      successfulDocCount: 0,
      failedCount: errors.length,
      durationMs: Date.now() - startedAt,
      error: "all_scrapes_failed",
    });
  } else {
    logger.info({
      event: "scrape.batch.completed",
      requestId: options?.requestId,
      concurrency: MAX_CONCURRENCY,
      requestedUrlCount: urls.length,
      successfulDocCount: results.length,
      failedCount: errors.length,
      durationMs: Date.now() - startedAt,
    });
  }

  return results;
}

function safeHost(url: string): string {
  try {
    return new URL(url).host;
  } catch {
    return "invalid_url";
  }
}
