import { NextRequest, NextResponse } from "next/server";
import { getLLMProxyConfig, LLMConfigError } from "@/lib/llm/config";
import { fetchProxyModels, LLMProxyError } from "@/lib/llm/proxy";
import {
  createRequestContext,
  logErrorEvent,
  logWideEvent,
} from "@/lib/logging/logger";

export async function GET(req: NextRequest) {
  const request = createRequestContext(req, "api.models");
  const startedAt = Date.now();
  const metrics: Record<string, unknown> = {};
  let statusCode = 500;
  let outcome: "success" | "error" = "error";
  let errorMeta: { name?: string; message?: string; code?: string | number; stage?: string } | undefined;
  const stage = "llm.models.fetch";

  const withRequestId = (response: NextResponse) => {
    response.headers.set("x-request-id", request.requestId);
    return response;
  };

  try {
    const modelFetchStartedAt = Date.now();
    const config = getLLMProxyConfig();
    const models = await fetchProxyModels(config);
    metrics.modelFetchDurationMs = Date.now() - modelFetchStartedAt;
    metrics.modelCount = models.length;

    if (models.length === 0) {
      statusCode = 502;
      return withRequestId(NextResponse.json(
        {
          error:
            "CLIProxyAPI returned no models from /v1/models. Check your proxy auths and model registrations.",
        },
        { status: 502 }
      ));
    }

    statusCode = 200;
    outcome = "success";
    return withRequestId(NextResponse.json({ models }));
  } catch (error) {
    errorMeta = {
      stage,
      ...(error instanceof Error
        ? { name: error.name, message: error.message }
        : { message: "Unknown error" }),
    };

    if (error instanceof LLMConfigError) {
      statusCode = 500;
      logErrorEvent("api.models.exception", request, error, stage);
      return withRequestId(
        NextResponse.json({ error: error.message }, { status: 500 })
      );
    }

    if (error instanceof LLMProxyError) {
      statusCode = 502;
      errorMeta.code = error.status;
      logErrorEvent("api.models.exception", request, error, stage);
      return withRequestId(NextResponse.json(
        {
          error:
            error.status === 401 || error.status === 403
              ? "CLIProxyAPI rejected credentials while fetching models."
              : error.status === 404
              ? "CLIProxyAPI returned 404 for model listing. Ensure the proxy serves OpenAI-compatible /v1 endpoints."
              : error.message,
        },
        { status: 502 }
      ));
    }

    statusCode = 502;
    logErrorEvent("api.models.exception", request, error, stage);
    return withRequestId(NextResponse.json(
      {
        error:
          error instanceof Error
            ? error.message
            : "Failed to fetch model list",
      },
      { status: 502 }
    ));
  } finally {
    logWideEvent({
      event: "api.models.completed",
      request,
      statusCode,
      outcome,
      durationMs: Date.now() - startedAt,
      metrics,
      error: errorMeta,
    });
  }
}
