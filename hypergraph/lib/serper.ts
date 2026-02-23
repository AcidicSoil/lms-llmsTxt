export async function searchDocs(topic: string): Promise<string[]> {
  const apiKey = process.env.SERPER_API_KEY;
  if (!apiKey) throw new Error("SERPER_API_KEY is not set");

  const res = await fetch("https://google.serper.dev/search", {
    method: "POST",
    headers: {
      "X-API-KEY": apiKey,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      q: `${topic} knowledge framework principles theory guide`,
      num: 20,
    }),
  });

  if (!res.ok) {
    throw new Error(`Serper search failed: ${res.status}`);
  }

  const data = await res.json();
  const blocked = [
    "youtube.com",
    "twitter.com",
    "x.com",
    "reddit.com",
    ".pdf",
  ];

  const urls: string[] = (data.organic ?? [])
    .map((r: { link: string }) => r.link)
    .filter(
      (url: string) => !blocked.some((b) => url.toLowerCase().includes(b))
    )
    .slice(0, 8);

  return urls;
}
