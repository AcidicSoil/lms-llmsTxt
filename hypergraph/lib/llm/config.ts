export interface LLMProxyConfig {
  baseUrl: string;
  apiKey?: string;
  defaultModel?: string;
}

export class LLMConfigError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "LLMConfigError";
  }
}

function trimTrailingSlash(value: string): string {
  return value.replace(/\/+$/, "");
}

export function normalizeCliproxyBaseUrl(raw: string): string {
  let parsed: URL;
  try {
    parsed = new URL(raw.trim());
  } catch {
    throw new LLMConfigError(
      `CLIPROXY_BASE_URL is not a valid URL: '${raw}'.`
    );
  }

  const pathname = trimTrailingSlash(parsed.pathname || "");
  if (pathname === "" || pathname === "/") {
    parsed.pathname = "/v1";
  } else if (!pathname.endsWith("/v1")) {
    parsed.pathname = `${pathname}/v1`;
  } else {
    parsed.pathname = pathname;
  }

  return trimTrailingSlash(parsed.toString());
}

export function getLLMProxyConfig(): LLMProxyConfig {
  const baseUrl = process.env.CLIPROXY_BASE_URL?.trim();
  if (!baseUrl) {
    throw new LLMConfigError(
      "CLIPROXY_BASE_URL is not set. Point it to your CLIProxyAPI OpenAI-compatible /v1 endpoint."
    );
  }

  return {
    baseUrl: normalizeCliproxyBaseUrl(baseUrl),
    apiKey: process.env.CLIPROXY_API_KEY?.trim() || undefined,
    defaultModel: process.env.DEFAULT_MODEL?.trim() || undefined,
  };
}
