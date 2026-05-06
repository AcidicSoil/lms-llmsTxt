import type { SearchProvider, SearchResult } from "@/lib/search/types";

interface TavilyResult {
  url?: string;
  title?: string;
  content?: string;
  score?: number;
}

interface TavilyResponse {
  results?: TavilyResult[];
}

export const tavilyProvider: SearchProvider = {
  name: "tavily",
  isConfigured: () => Boolean(process.env.TAVILY_API_KEY),
  async search(query, options) {
    const apiKey = process.env.TAVILY_API_KEY;
    if (!apiKey) {
      throw new Error("TAVILY_API_KEY is not set");
    }

    const response = await fetch("https://api.tavily.com/search", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify({
        query,
        topic: "general",
        search_depth: "basic",
        max_results: options.maxResults * 2,
      }),
    });

    if (!response.ok) {
      throw new Error(`Tavily search failed: ${response.status}`);
    }

    const data = (await response.json()) as TavilyResponse;
    return (data.results ?? [])
      .filter((item) => typeof item.url === "string")
      .map(
        (item): SearchResult => ({
          url: item.url as string,
          title: item.title,
          snippet: item.content,
          score: item.score,
        })
      );
  },
};
