export type SearchProviderName = "serper" | "brave" | "tavily";

export interface SearchOptions {
  maxResults: number;
}

export interface SearchResult {
  url: string;
  title?: string;
  snippet?: string;
  score?: number;
}

export interface SearchProvider {
  name: SearchProviderName;
  isConfigured: () => boolean;
  search: (query: string, options: SearchOptions) => Promise<SearchResult[]>;
}

export interface ProviderAttempt {
  provider: SearchProviderName;
  ok: boolean;
  reason?: string;
  resultCount?: number;
}

export interface SearchDiagnostics {
  attempted: ProviderAttempt[];
  selected?: SearchProviderName;
}
