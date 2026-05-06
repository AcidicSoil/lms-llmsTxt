import { NextRequest, NextResponse } from "next/server";
import { listGenerations } from "@/lib/db/repository/generations";
import { logger } from "@/lib/logging/logger";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  const requestId = req.headers.get("x-request-id") || crypto.randomUUID();
  try {
    const limitRaw = req.nextUrl.searchParams.get("limit");
    const limit = limitRaw ? Number.parseInt(limitRaw, 10) : 50;
    const generations = await listGenerations(limit);

    logger.info({
      event: "db.generation.list.completed",
      requestId,
      count: generations.length,
      limit,
    });

    const response = NextResponse.json({ generations });
    response.headers.set("x-request-id", requestId);
    return response;
  } catch (error) {
    logger.error({
      event: "db.generation.list.failed",
      requestId,
      error: error instanceof Error ? error.message : "unknown_error",
    });
    const response = NextResponse.json(
      { error: "Failed to list generations" },
      { status: 500 }
    );
    response.headers.set("x-request-id", requestId);
    return response;
  }
}
