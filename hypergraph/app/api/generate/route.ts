import { NextRequest, NextResponse } from "next/server";
import { searchDocs } from "@/lib/serper";
import { scrapeUrls, ConcurrencyPlanError } from "@/lib/hyperbrowser";
import {
  generateGraph,
  generateRepoGraph,
  loadRepoGraph,
  type GenerationTrace,
  type GenerationTraceContext,
} from "@/lib/generator";
import { errorToLog, logger, preview } from "@/lib/logger";
import type { GeneratedFile, SkillGraph } from "@/types/graph";

export const maxDuration = 60;
export const runtime = "nodejs";

type GenerateMode = "topic" | "generate-repo-graph" | "load-repo-graph";

type RequestLogEvent = {
  event: "hypergraph.generate";
  requestId: string;
  mode: GenerateMode;
  startedAt: string;
  durationMs?: number;
  statusCode?: number;
  outcome?: "success" | "error";
  input?: Record<string, unknown>;
  graph?: {
    topic?: string;
    nodeCount?: number;
    fileCount?: number;
    artifactPath?: string;
  };
  trace?: GenerationTrace;
  error?: ReturnType<typeof errorToLog>;
};

function jsonWithRequestId(
  body: Record<string, unknown>,
  requestId: string,
  init?: ResponseInit,
) {
  return NextResponse.json({ ...body, requestId }, init);
}

function finalizeLog(
  event: RequestLogEvent,
  startedMs: number,
  statusCode: number,
  outcome: "success" | "error",
  extra: Partial<RequestLogEvent> = {},
) {
  const finalEvent: RequestLogEvent = {
    ...event,
    ...extra,
    statusCode,
    outcome,
    durationMs: Date.now() - startedMs,
  };

  if (outcome === "error") {
    logger.error(finalEvent);
    return;
  }

  logger.info(finalEvent);
}

function inputSummary({
  mode,
  topic,
  graphPath,
  repoUrl,
}: {
  mode: GenerateMode;
  topic: unknown;
  graphPath: unknown;
  repoUrl: unknown;
}): Record<string, unknown> {
  if (mode === "load-repo-graph") {
    const value = typeof graphPath === "string" ? graphPath : "";
    return {
      graphPath: value ? preview(value, 180) : undefined,
      graphPathLength: value.length,
    };
  }

  if (mode === "generate-repo-graph") {
    if (typeof repoUrl !== "string") return {};
    try {
      const parsed = new URL(repoUrl);
      const parts = parsed.pathname.replace(/^\/+|\/+$/g, "").split("/");
      return {
        repoHost: parsed.hostname,
        repoOwner: parts[0],
        repoName: parts[1]?.replace(/\.git$/i, ""),
      };
    } catch {
      return { repoUrlPreview: preview(repoUrl, 120) };
    }
  }

  const value = typeof topic === "string" ? topic.trim() : "";
  return {
    topicPreview: value ? preview(value, 120) : undefined,
    topicLength: value.length,
  };
}

function graphSummary(
  graph: SkillGraph,
  files: GeneratedFile[],
  artifactPath?: string,
): RequestLogEvent["graph"] {
  return {
    topic: graph.topic,
    nodeCount: graph.nodes.length,
    fileCount: files.length,
    artifactPath,
  };
}

export async function POST(req: NextRequest) {
  const requestId = crypto.randomUUID();
  const startedMs = Date.now();
  let parsedBody: {
    topic?: unknown;
    mode?: unknown;
    graphPath?: unknown;
    repoUrl?: unknown;
  } = {};
  let mode: GenerateMode = "topic";

  const baseEvent: RequestLogEvent = {
    event: "hypergraph.generate",
    requestId,
    mode,
    startedAt: new Date(startedMs).toISOString(),
  };

  try {
    parsedBody = await req.json();
    const { topic, graphPath, repoUrl } = parsedBody;
    mode =
      parsedBody.mode === "load-repo-graph" ||
      parsedBody.mode === "generate-repo-graph"
        ? parsedBody.mode
        : "topic";
    baseEvent.mode = mode;
    baseEvent.input = inputSummary({ mode, topic, graphPath, repoUrl });

    const traceContext: GenerationTraceContext = { requestId, mode };

    if (mode === "load-repo-graph") {
      if (!graphPath || typeof graphPath !== "string") {
        const error = new Error("graphPath is required in load-repo-graph mode");
        finalizeLog(baseEvent, startedMs, 400, "error", { error: errorToLog(error) });
        return jsonWithRequestId({ error: error.message }, requestId, { status: 400 });
      }
      try {
        const { graph, files, trace } = await loadRepoGraph(graphPath, traceContext);
        finalizeLog(baseEvent, startedMs, 200, "success", {
          graph: graphSummary(graph, files),
          trace,
        });
        return jsonWithRequestId({ graph, files, trace }, requestId);
      } catch (error) {
        finalizeLog(baseEvent, startedMs, 400, "error", { error: errorToLog(error) });
        return jsonWithRequestId(
          {
            error:
              error instanceof Error ? error.message : "Invalid graph path",
          },
          requestId,
          { status: 400 },
        );
      }
    }

    if (mode === "generate-repo-graph") {
      if (!repoUrl || typeof repoUrl !== "string") {
        const error = new Error("repoUrl is required in generate-repo-graph mode");
        finalizeLog(baseEvent, startedMs, 400, "error", { error: errorToLog(error) });
        return jsonWithRequestId({ error: error.message }, requestId, { status: 400 });
      }
      try {
        const { graph, files, artifactPath, trace } = await generateRepoGraph(
          repoUrl,
          traceContext,
        );
        finalizeLog(baseEvent, startedMs, 200, "success", {
          graph: graphSummary(graph, files, artifactPath),
          trace,
        });
        return jsonWithRequestId({ graph, files, artifactPath, trace }, requestId);
      } catch (error) {
        finalizeLog(baseEvent, startedMs, 400, "error", { error: errorToLog(error) });
        return jsonWithRequestId(
          {
            error:
              error instanceof Error
                ? error.message
                : "Repo graph generation failed",
          },
          requestId,
          { status: 400 },
        );
      }
    }

    if (!topic || typeof topic !== "string" || topic.trim().length === 0) {
      const error = new Error("Topic is required");
      finalizeLog(baseEvent, startedMs, 400, "error", { error: errorToLog(error) });
      return jsonWithRequestId({ error: error.message }, requestId, { status: 400 });
    }

    const urls = await searchDocs(topic.trim());
    if (urls.length === 0) {
      const error = new Error("No documentation found for this topic");
      finalizeLog(baseEvent, startedMs, 404, "error", {
        error: errorToLog(error),
        trace: { requestId, mode, provider: "serper", durationMs: Date.now() - startedMs },
      });
      return jsonWithRequestId({ error: error.message }, requestId, { status: 404 });
    }

    const docs = await scrapeUrls(urls);
    if (docs.length === 0) {
      const error = new Error("Failed to scrape any documentation");
      finalizeLog(baseEvent, startedMs, 502, "error", {
        error: errorToLog(error),
        trace: {
          requestId,
          mode,
          provider: "hyperbrowser",
          durationMs: Date.now() - startedMs,
          promptSourceCount: urls.length,
        },
      });
      return jsonWithRequestId({ error: error.message }, requestId, { status: 502 });
    }

    const { graph, files, trace } = await generateGraph(
      topic.trim(),
      docs,
      traceContext,
    );

    finalizeLog(baseEvent, startedMs, 200, "success", {
      graph: graphSummary(graph, files),
      trace,
    });
    return jsonWithRequestId({ graph, files, trace }, requestId);
  } catch (err) {
    if (err instanceof ConcurrencyPlanError) {
      finalizeLog(baseEvent, startedMs, 402, "error", { error: errorToLog(err) });
      return jsonWithRequestId(
        {
          error: err.message,
          upgradeUrl: "https://hyperbrowser.ai",
          hint: "Set HYPERBROWSER_MAX_CONCURRENCY=1 in your .env (it is already the default) and ensure no other requests are running simultaneously.",
        },
        requestId,
        { status: 402 },
      );
    }
    finalizeLog(baseEvent, startedMs, 500, "error", { error: errorToLog(err) });
    return jsonWithRequestId(
      { error: err instanceof Error ? err.message : "Internal server error" },
      requestId,
      { status: 500 },
    );
  }
}
