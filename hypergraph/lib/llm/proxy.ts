import type { LLMProxyConfig } from "@/lib/llm/config";
import { logger } from "@/lib/logging/logger";

export interface ModelOption {
  id: string;
  label: string;
}

interface OpenAIModelsResponse {
  data?: Array<{ id?: string }>;
}

export class LLMProxyError extends Error {
  status?: number;

  constructor(message: string, status?: number) {
    super(message);
    this.name = "LLMProxyError";
    this.status = status;
  }
}

function buildProxyUrl(baseUrl: string, endpoint: string): string {
  return `${baseUrl}${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`;
}

function authHeaders(config: LLMProxyConfig): HeadersInit {
  if (!config.apiKey) {
    return { "Content-Type": "application/json" };
  }
  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${config.apiKey}`,
  };
}

export async function fetchProxyModels(
  config: LLMProxyConfig
): Promise<ModelOption[]> {
  const startedAt = Date.now();
  const response = await fetch(buildProxyUrl(config.baseUrl, "/models"), {
    method: "GET",
    headers: authHeaders(config),
    cache: "no-store",
  });

  if (!response.ok) {
    logger.error({
      event: "llm.models.fetch.failed",
      statusCode: response.status,
      durationMs: Date.now() - startedAt,
    });
    throw new LLMProxyError(
      `Failed to fetch models from CLIProxyAPI: ${response.status}`,
      response.status
    );
  }

  const json = (await response.json()) as OpenAIModelsResponse;
  const ids = (json.data ?? [])
    .map((item) => (typeof item.id === "string" ? item.id.trim() : ""))
    .filter(Boolean);

  const deduped = Array.from(new Set(ids)).sort((a, b) =>
    a.localeCompare(b, "en")
  );

  logger.info({
    event: "llm.models.fetch.completed",
    modelCount: deduped.length,
    durationMs: Date.now() - startedAt,
  });

  return deduped.map((id) => ({ id, label: id }));
}

export function resolveModelSelection(
  requestedModel: string | undefined,
  defaultModel: string | undefined
): string | null {
  const selected = requestedModel?.trim() || defaultModel?.trim() || "";
  return selected.length > 0 ? selected : null;
}
