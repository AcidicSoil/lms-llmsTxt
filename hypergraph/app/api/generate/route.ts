import { NextRequest, NextResponse } from "next/server";
import { SearchConfigError, SearchNoResultsError, searchDocs } from "@/lib/search";
import { scrapeUrls, ConcurrencyPlanError } from "@/lib/hyperbrowser";
import {
  generateGraph,
  generateRepoGraph,
  loadRepoGraph,
  type GenerationTrace,
  type GenerationTraceContext,
} from "@/lib/generator";
import { getLLMProxyConfig, LLMConfigError } from "@/lib/llm/config";
import { fetchProxyModels, LLMProxyError, resolveModelSelection } from "@/lib/llm/proxy";
import { createGeneration } from "@/lib/db/repository/generations";
import {
  createRequestContext,
  logErrorEvent,
  logProgressEvent,
  logWideEvent,
  type GenerationStage,
} from "@/lib/logging/logger";

export const maxDuration = 60;
export const runtime = "nodejs";

type GenerateMode = "topic" | "generate-repo-graph" | "load-repo-graph";

type AppErrorMeta = { name?: string; message?: string; code?: string | number; stage?: string };

function withRequestId(response: NextResponse, requestId: string): NextResponse {
  response.headers.set("x-request-id", requestId);
  return response;
}


export async function POST(req: NextRequest) {
  const request = createRequestContext(req, "api.generate");
  const startedAt = Date.now();
  const metrics: Record<string, unknown> = {};
  let statusCode = 500;
  let outcome: "success" | "error" = "error";
  let errorMeta: AppErrorMeta | undefined;
  let stage: GenerationStage = "request.parse";
  let stageStartedAt = Date.now();

  const markStageStart = (nextStage: GenerationStage, stageMetrics?: Record<string, unknown>) => {
    stage = nextStage;
    stageStartedAt = Date.now();
    logProgressEvent({ event: "api.generate.stage.started", request, stage, metrics: stageMetrics });
  };

  const markStageSuccess = (stageMetrics?: Record<string, unknown>) => {
    logProgressEvent({
      event: "api.generate.stage.succeeded",
      request,
      stage,
      durationMs: Date.now() - stageStartedAt,
      metrics: stageMetrics,
    });
  };

  try {
    markStageStart("request.parse");
    const { topic, model, mode: rawMode, graphPath, repoUrl } = await req.json();
    const mode: GenerateMode =
      rawMode === "load-repo-graph" || rawMode === "generate-repo-graph" ? rawMode : "topic";
    const traceContext: GenerationTraceContext = { requestId: request.requestId, mode };
    metrics.mode = mode;
    metrics.hasModelInput = typeof model === "string" && model.trim().length > 0;
    markStageSuccess({ mode, hasModelInput: metrics.hasModelInput });

    if (mode === "load-repo-graph") {
      markStageStart("llm.generate", { mode });
      if (!graphPath || typeof graphPath !== "string") {
        statusCode = 400;
        return withRequestId(NextResponse.json({ error: "graphPath is required in load-repo-graph mode" }, { status: 400 }), request.requestId);
      }
      const { graph, files, trace } = await loadRepoGraph(graphPath, traceContext);
      metrics.graphNodeCount = graph.nodes.length;
      metrics.generatedFileCount = files.length;
      markStageSuccess({ graphNodeCount: graph.nodes.length, generatedFileCount: files.length });
      statusCode = 200;
      outcome = "success";
      return withRequestId(NextResponse.json({ graph, files, trace, requestId: request.requestId }), request.requestId);
    }

    if (mode === "generate-repo-graph") {
      markStageStart("llm.generate", { mode });
      if (!repoUrl || typeof repoUrl !== "string") {
        statusCode = 400;
        return withRequestId(NextResponse.json({ error: "repoUrl is required in generate-repo-graph mode" }, { status: 400 }), request.requestId);
      }
      const { graph, files, artifactPath, trace } = await generateRepoGraph(repoUrl, traceContext);
      metrics.graphNodeCount = graph.nodes.length;
      metrics.generatedFileCount = files.length;
      metrics.artifactPath = artifactPath;
      markStageSuccess({ graphNodeCount: graph.nodes.length, generatedFileCount: files.length, artifactPath });
      statusCode = 200;
      outcome = "success";
      return withRequestId(NextResponse.json({ graph, files, artifactPath, trace, requestId: request.requestId }), request.requestId);
    }

    if (!topic || typeof topic !== "string" || topic.trim().length === 0) {
      statusCode = 400;
      return withRequestId(NextResponse.json({ error: "Topic is required" }, { status: 400 }), request.requestId);
    }

    markStageStart("search.docs");
    const searchStartedAt = Date.now();
    const { urls, diagnostics } = await searchDocs(topic.trim());
    metrics.searchDurationMs = Date.now() - searchStartedAt;
    metrics.searchAttempts = diagnostics.attempted.length;
    metrics.selectedSearchProvider = diagnostics.selected;
    metrics.urlsFound = urls.length;
    markStageSuccess({ urlsFound: urls.length, selectedSearchProvider: diagnostics.selected });

    markStageStart("scrape.urls", { urlsToScrape: urls.length });
    const scrapeStartedAt = Date.now();
    const docs = await scrapeUrls(urls, { requestId: request.requestId });
    metrics.scrapeDurationMs = Date.now() - scrapeStartedAt;
    metrics.docsScraped = docs.length;
    if (docs.length === 0) {
      statusCode = 502;
      return withRequestId(NextResponse.json({ error: "Failed to scrape any documentation" }, { status: 502 }), request.requestId);
    }
    markStageSuccess({ docsScraped: docs.length });

    markStageStart("llm.models.fetch");
    const llmConfig = getLLMProxyConfig();
    const selectedModel = resolveModelSelection(typeof model === "string" ? model : undefined, llmConfig.defaultModel);
    if (!selectedModel) {
      statusCode = 400;
      return withRequestId(NextResponse.json({ error: "No model selected. Pick a model in the UI or set DEFAULT_MODEL." }, { status: 400 }), request.requestId);
    }
    const models = await fetchProxyModels(llmConfig);
    if (!models.some((available) => available.id === selectedModel)) {
      statusCode = 400;
      return withRequestId(NextResponse.json({ error: `Model '${selectedModel}' is not available from CLIProxyAPI /v1/models.` }, { status: 400 }), request.requestId);
    }
    metrics.selectedModel = selectedModel;
    metrics.availableModelCount = models.length;
    markStageSuccess({ selectedModel, availableModelCount: models.length });

    markStageStart("llm.generate", { selectedModel, docsScraped: docs.length });
    const generateStartedAt = Date.now();
    const { graph, files, trace } = await generateGraph(topic.trim(), docs, traceContext, selectedModel);
    metrics.generateDurationMs = Date.now() - generateStartedAt;
    metrics.graphNodeCount = graph.nodes.length;
    metrics.generatedFileCount = files.length;
    markStageSuccess({ graphNodeCount: graph.nodes.length, generatedFileCount: files.length });

    let generationId: string | undefined;
    let persistenceWarning: "store_failed" | undefined;
    try {
      generationId = crypto.randomUUID();
      await createGeneration({
        id: generationId,
        requestId: request.requestId,
        topic: topic.trim(),
        model: selectedModel,
        status: "success",
        searchProvider: diagnostics.selected ?? null,
        searchAttempts: diagnostics.attempted,
        graph,
        files,
        metrics,
      });
    } catch {
      persistenceWarning = "store_failed";
    }

    statusCode = 200;
    outcome = "success";
    return withRequestId(NextResponse.json({
      graph,
      files,
      trace: trace satisfies GenerationTrace | undefined,
      meta: {
        generationId,
        model: selectedModel,
        searchProvider: diagnostics.selected,
        searchAttempts: diagnostics.attempted,
        requestId: request.requestId,
        persistenceWarning,
      },
    }), request.requestId);
  } catch (err) {
    logProgressEvent({ event: "api.generate.stage.failed", request, stage, durationMs: Date.now() - stageStartedAt, error: err });
    errorMeta = {
      stage,
      ...(err instanceof Error ? { name: err.name, message: err.message } : { message: "Unknown error" }),
    };

    if (err instanceof LLMConfigError || err instanceof SearchConfigError) {
      statusCode = 500;
      logErrorEvent("api.generate.exception", request, err, stage);
      return withRequestId(NextResponse.json({ error: err.message }, { status: 500 }), request.requestId);
    }
    if (err instanceof LLMProxyError) {
      statusCode = 502;
      errorMeta.code = err.status;
      logErrorEvent("api.generate.exception", request, err, stage);
      return withRequestId(NextResponse.json({ error: err.message }, { status: 502 }), request.requestId);
    }
    if (err instanceof SearchNoResultsError) {
      statusCode = 404;
      logErrorEvent("api.generate.exception", request, err, stage);
      return withRequestId(NextResponse.json({ error: err.message, meta: { searchAttempts: err.diagnostics.attempted } }, { status: 404 }), request.requestId);
    }
    if (err instanceof ConcurrencyPlanError) {
      statusCode = 402;
      logErrorEvent("api.generate.exception", request, err, stage);
      return withRequestId(NextResponse.json({
        error: err.message,
        upgradeUrl: "https://hyperbrowser.ai",
        hint: "Set HYPERBROWSER_MAX_CONCURRENCY=1 in your .env and ensure no other requests are running simultaneously.",
      }, { status: 402 }), request.requestId);
    }
    statusCode = 500;
    logErrorEvent("api.generate.exception", request, err, stage);
    return withRequestId(NextResponse.json({ error: err instanceof Error ? err.message : "Internal server error" }, { status: 500 }), request.requestId);
  } finally {
    logWideEvent({
      event: "api.generate.completed",
      request,
      statusCode,
      outcome,
      durationMs: Date.now() - startedAt,
      metrics,
      error: errorMeta,
    });
  }
}
