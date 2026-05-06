import { NextRequest, NextResponse } from "next/server";
import {
  deleteGenerationById,
  getGenerationById,
} from "@/lib/db/repository/generations";
import { logger } from "@/lib/logging/logger";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(
  req: NextRequest,
  context: { params: Promise<{ id: string }> }
) {
  const requestId = req.headers.get("x-request-id") || crypto.randomUUID();
  const { id } = await context.params;
  try {
    const generation = await getGenerationById(id);
    if (!generation) {
      const response = NextResponse.json(
        { error: "Generation not found" },
        { status: 404 }
      );
      response.headers.set("x-request-id", requestId);
      return response;
    }

    logger.info({
      event: "db.generation.get.completed",
      requestId,
      id,
    });

    const response = NextResponse.json(generation);
    response.headers.set("x-request-id", requestId);
    return response;
  } catch (error) {
    logger.error({
      event: "db.generation.get.failed",
      requestId,
      id,
      error: error instanceof Error ? error.message : "unknown_error",
    });
    const response = NextResponse.json(
      { error: "Failed to fetch generation" },
      { status: 500 }
    );
    response.headers.set("x-request-id", requestId);
    return response;
  }
}

export async function DELETE(
  req: NextRequest,
  context: { params: Promise<{ id: string }> }
) {
  const requestId = req.headers.get("x-request-id") || crypto.randomUUID();
  const { id } = await context.params;
  try {
    const deleted = await deleteGenerationById(id);
    if (!deleted) {
      const response = NextResponse.json(
        { error: "Generation not found" },
        { status: 404 }
      );
      response.headers.set("x-request-id", requestId);
      return response;
    }

    logger.info({
      event: "db.generation.delete.completed",
      requestId,
      id,
    });
    const response = new NextResponse(null, { status: 204 });
    response.headers.set("x-request-id", requestId);
    return response;
  } catch (error) {
    logger.error({
      event: "db.generation.delete.failed",
      requestId,
      id,
      error: error instanceof Error ? error.message : "unknown_error",
    });
    const response = NextResponse.json(
      { error: "Failed to delete generation" },
      { status: 500 }
    );
    response.headers.set("x-request-id", requestId);
    return response;
  }
}
