import { braveProvider } from "@/lib/search/providers/brave";
import { serperProvider } from "@/lib/search/providers/serper";
import { tavilyProvider } from "@/lib/search/providers/tavily";
import type {
  SearchDiagnostics,
  SearchProvider,
  SearchProviderName,
} from "@/lib/search/types";
import { normalizeResults, parseMaxResults, toSearchQuery } from "@/lib/search/utils";
import { logger } from "@/lib/logging/logger";

const DEFAULT_PROVIDER_ORDER: SearchProviderName[] = [
  "serper",
  "brave",
  "tavily",
];

const providers: Record<SearchProviderName, SearchProvider> = {
  serper: serperProvider,
  brave: braveProvider,
  tavily: tavilyProvider,
};

export class SearchConfigError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "SearchConfigError";
  }
}

export class SearchNoResultsError extends Error {
  diagnostics: SearchDiagnostics;

  constructor(message: string, diagnostics: SearchDiagnostics) {
    super(message);
    this.name = "SearchNoResultsError";
    this.diagnostics = diagnostics;
  }
}

function getProviderOrder(): SearchProviderName[] {
  const raw = process.env.SEARCH_PROVIDER_ORDER;
  if (!raw) return DEFAULT_PROVIDER_ORDER;

  const parsed = raw
    .split(",")
    .map((value) => value.trim().toLowerCase())
    .filter((value): value is SearchProviderName =>
      value === "serper" || value === "brave" || value === "tavily"
    );

  if (parsed.length === 0) return DEFAULT_PROVIDER_ORDER;

  const seen = new Set<SearchProviderName>();
  return parsed.filter((provider) => {
    if (seen.has(provider)) return false;
    seen.add(provider);
    return true;
  });
}

function toReason(error: unknown): string {
  if (error instanceof Error) {
    const msg = error.message.toLowerCase();
    if (msg.includes("not set")) return "not_configured";
    if (msg.includes("401") || msg.includes("403")) return "auth_failed";
    return "request_failed";
  }
  return "request_failed";
}

export async function searchDocs(
  topic: string
): Promise<{ urls: string[]; diagnostics: SearchDiagnostics }> {
  const startedAt = Date.now();
  const order = getProviderOrder();
  const query = toSearchQuery(topic);
  const maxResults = parseMaxResults(process.env.SEARCH_MAX_RESULTS, 8);
  const attempted: SearchDiagnostics["attempted"] = [];

  let configuredProviders = 0;

  for (const name of order) {
    const provider = providers[name];
    const providerStartedAt = Date.now();

    if (!provider.isConfigured()) {
      attempted.push({ provider: name, ok: false, reason: "not_configured" });
      logger.info({
        event: "search.provider.attempt",
        provider: name,
        configured: false,
        reason: "not_configured",
      });
      continue;
    }

    configuredProviders += 1;

    try {
      const results = await provider.search(query, { maxResults });
      const urls = normalizeResults(results, maxResults);

      if (urls.length === 0) {
        attempted.push({
          provider: name,
          ok: false,
          reason: "empty_results",
          resultCount: 0,
        });
        logger.info({
          event: "search.provider.attempt",
          provider: name,
          configured: true,
          ok: false,
          reason: "empty_results",
          durationMs: Date.now() - providerStartedAt,
        });
        continue;
      }

      attempted.push({
        provider: name,
        ok: true,
        reason: "ok",
        resultCount: urls.length,
      });

      logger.info({
        event: "search.provider.selected",
        provider: name,
        configured: true,
        ok: true,
        resultCount: urls.length,
        attemptedProviders: attempted.length,
        queryLength: query.length,
        durationMs: Date.now() - providerStartedAt,
        totalDurationMs: Date.now() - startedAt,
      });

      return {
        urls,
        diagnostics: {
          attempted,
          selected: name,
        },
      };
    } catch (error) {
      const reason = toReason(error);
      attempted.push({
        provider: name,
        ok: false,
        reason,
      });
      logger.warn({
        event: "search.provider.attempt",
        provider: name,
        configured: true,
        ok: false,
        reason,
        durationMs: Date.now() - providerStartedAt,
        error: error instanceof Error ? { name: error.name, message: error.message } : "unknown_error",
      });
    }
  }

  logger.warn({
    event: "search.provider.exhausted",
    attemptedProviders: attempted.length,
    configuredProviders,
    totalDurationMs: Date.now() - startedAt,
    queryLength: query.length,
    diagnostics: attempted,
  });

  if (configuredProviders === 0) {
    throw new SearchConfigError(
      "No search providers are configured. Set at least one of SERPER_API_KEY, BRAVE_API_KEY, or TAVILY_API_KEY."
    );
  }

  throw new SearchNoResultsError("No documentation found for this topic", {
    attempted,
  });
}
