import type { SearchProvider, SearchResult } from "@/lib/search/types";

interface SerperOrganicResult {
  link?: string;
  title?: string;
  snippet?: string;
}

interface SerperResponse {
  organic?: SerperOrganicResult[];
}

export const serperProvider: SearchProvider = {
  name: "serper",
  isConfigured: () => Boolean(process.env.SERPER_API_KEY),
  async search(query, options) {
    const apiKey = process.env.SERPER_API_KEY;
    if (!apiKey) {
      throw new Error("SERPER_API_KEY is not set");
    }

    const response = await fetch("https://google.serper.dev/search", {
      method: "POST",
      headers: {
        "X-API-KEY": apiKey,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        q: query,
        num: options.maxResults * 2,
      }),
    });

    if (!response.ok) {
      throw new Error(`Serper search failed: ${response.status}`);
    }

    const data = (await response.json()) as SerperResponse;
    return (data.organic ?? [])
      .filter((item) => typeof item.link === "string")
      .map(
        (item): SearchResult => ({
          url: item.link as string,
          title: item.title,
          snippet: item.snippet,
        })
      );
  },
};
