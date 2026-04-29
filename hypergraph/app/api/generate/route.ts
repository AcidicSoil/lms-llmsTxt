import { NextRequest, NextResponse } from "next/server";
import { searchDocs } from "@/lib/serper";
import { scrapeUrls, ConcurrencyPlanError } from "@/lib/hyperbrowser";
import {
  generateGraph,
  generateRepoGraph,
  loadRepoGraph,
} from "@/lib/generator";

export const maxDuration = 60;
export const runtime = "nodejs";

export async function POST(req: NextRequest) {
  try {
    const { topic, mode, graphPath, repoUrl } = await req.json();

    if (mode === "load-repo-graph") {
      if (!graphPath || typeof graphPath !== "string") {
        return NextResponse.json(
          { error: "graphPath is required in load-repo-graph mode" },
          { status: 400 },
        );
      }
      try {
        const { graph, files } = await loadRepoGraph(graphPath);
        return NextResponse.json({ graph, files });
      } catch (error) {
        return NextResponse.json(
          {
            error:
              error instanceof Error ? error.message : "Invalid graph path",
          },
          { status: 400 },
        );
      }
    }

    if (mode === "generate-repo-graph") {
      if (!repoUrl || typeof repoUrl !== "string") {
        return NextResponse.json(
          { error: "repoUrl is required in generate-repo-graph mode" },
          { status: 400 },
        );
      }
      try {
        const { graph, files, artifactPath } = await generateRepoGraph(repoUrl);
        return NextResponse.json({ graph, files, artifactPath });
      } catch (error) {
        return NextResponse.json(
          {
            error:
              error instanceof Error
                ? error.message
                : "Repo graph generation failed",
          },
          { status: 400 },
        );
      }
    }

    if (!topic || typeof topic !== "string" || topic.trim().length === 0) {
      return NextResponse.json({ error: "Topic is required" }, { status: 400 });
    }

    const urls = await searchDocs(topic.trim());
    if (urls.length === 0) {
      return NextResponse.json(
        { error: "No documentation found for this topic" },
        { status: 404 },
      );
    }

    const docs = await scrapeUrls(urls);
    if (docs.length === 0) {
      return NextResponse.json(
        { error: "Failed to scrape any documentation" },
        { status: 502 },
      );
    }

    const { graph, files } = await generateGraph(topic.trim(), docs);

    return NextResponse.json({ graph, files });
  } catch (err) {
    if (err instanceof ConcurrencyPlanError) {
      console.warn("[generate] Concurrency plan limit hit:", err.message);
      return NextResponse.json(
        {
          error: err.message,
          upgradeUrl: "https://hyperbrowser.ai",
          hint: "Set HYPERBROWSER_MAX_CONCURRENCY=1 in your .env (it is already the default) and ensure no other requests are running simultaneously.",
        },
        { status: 402 },
      );
    }
    console.error("Generate error:", err);
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "Internal server error" },
      { status: 500 },
    );
  }
}
