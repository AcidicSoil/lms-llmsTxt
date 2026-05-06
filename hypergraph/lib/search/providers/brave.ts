import type { SearchProvider, SearchResult } from "@/lib/search/types";

interface BraveWebResult {
  url?: string;
  title?: string;
  description?: string;
}

interface BraveWebResponse {
  web?: {
    results?: BraveWebResult[];
  };
}

export const braveProvider: SearchProvider = {
  name: "brave",
  isConfigured: () => Boolean(process.env.BRAVE_API_KEY),
  async search(query, options) {
    const apiKey = process.env.BRAVE_API_KEY;
    if (!apiKey) {
      throw new Error("BRAVE_API_KEY is not set");
    }

    const url = new URL("https://api.search.brave.com/res/v1/web/search");
    url.searchParams.set("q", query);
    url.searchParams.set("count", String(Math.min(options.maxResults * 2, 20)));
    url.searchParams.set("search_lang", "en");
    url.searchParams.set("country", "us");

    const response = await fetch(url, {
      method: "GET",
      headers: {
        Accept: "application/json",
        "X-Subscription-Token": apiKey,
      },
    });

    if (!response.ok) {
      throw new Error(`Brave search failed: ${response.status}`);
    }

    const data = (await response.json()) as BraveWebResponse;
    return (data.web?.results ?? [])
      .filter((item) => typeof item.url === "string")
      .map(
        (item): SearchResult => ({
          url: item.url as string,
          title: item.title,
          snippet: item.description,
        })
      );
  },
};
