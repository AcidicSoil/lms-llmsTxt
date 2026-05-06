import { desc, eq } from "drizzle-orm";
import { getDb } from "@/lib/db/client";
import { generations, type GenerationRow, type NewGenerationRow } from "@/lib/db/schema";
import type {
  GeneratedFile,
  GenerationRecordDetail,
  GenerationRecordSummary,
  SkillGraph,
} from "@/types/graph";
import type { SearchProviderName } from "@/lib/search/types";

interface SearchAttempt {
  provider: SearchProviderName;
  ok: boolean;
  reason?: string;
  resultCount?: number;
}

export interface CreateGenerationInput {
  id: string;
  requestId: string;
  topic: string;
  model: string | null;
  status: "success" | "error";
  searchProvider: SearchProviderName | null;
  searchAttempts: SearchAttempt[];
  graph: SkillGraph;
  files: GeneratedFile[];
  metrics?: Record<string, unknown>;
  error?: Record<string, unknown>;
}

export async function createGeneration(
  input: CreateGenerationInput
): Promise<void> {
  const db = getDb();
  const now = Date.now();
  const row: NewGenerationRow = {
    id: input.id,
    createdAt: now,
    updatedAt: now,
    requestId: input.requestId,
    topic: input.topic,
    model: input.model,
    status: input.status,
    searchProvider: input.searchProvider,
    searchAttemptsJson: JSON.stringify(input.searchAttempts),
    graphJson: JSON.stringify(input.graph),
    filesJson: JSON.stringify(input.files),
    metricsJson: input.metrics ? JSON.stringify(input.metrics) : null,
    errorJson: input.error ? JSON.stringify(input.error) : null,
  };
  db.insert(generations).values(row).run();
}

export async function listGenerations(
  limit = 50
): Promise<GenerationRecordSummary[]> {
  const db = getDb();
  const rows = db
    .select()
    .from(generations)
    .orderBy(desc(generations.createdAt))
    .limit(Math.max(1, Math.min(limit, 200)))
    .all();

  return rows.map((row) => {
    const graph = parseJson<SkillGraph | null>(row.graphJson, null);
    const files = parseJson<GeneratedFile[] | null>(row.filesJson, null);
    return {
      id: row.id,
      topic: row.topic,
      model: row.model ?? null,
      status: toStatus(row.status),
      requestId: row.requestId,
      searchProvider: toSearchProvider(row.searchProvider),
      nodeCount: graph?.nodes?.length ?? 0,
      fileCount: files?.length ?? 0,
      createdAt: row.createdAt,
    };
  });
}

export async function getGenerationById(
  id: string
): Promise<GenerationRecordDetail | null> {
  const db = getDb();
  const row = db.select().from(generations).where(eq(generations.id, id)).get();
  if (!row) return null;
  return toDetail(row);
}

export async function deleteGenerationById(id: string): Promise<boolean> {
  const db = getDb();
  const result = db.delete(generations).where(eq(generations.id, id)).run();
  return result.changes > 0;
}

function toDetail(row: GenerationRow): GenerationRecordDetail {
  return {
    id: row.id,
    topic: row.topic,
    model: row.model ?? null,
    status: toStatus(row.status),
    requestId: row.requestId,
    searchProvider: toSearchProvider(row.searchProvider),
    searchAttempts: parseJson<SearchAttempt[]>(row.searchAttemptsJson, []),
    graph: parseJson<SkillGraph>(row.graphJson, { topic: row.topic, nodes: [] }),
    files: parseJson<GeneratedFile[]>(row.filesJson, []),
    metrics: parseJson<Record<string, unknown> | undefined>(
      row.metricsJson,
      undefined
    ),
    error: parseJson<Record<string, unknown> | undefined>(
      row.errorJson,
      undefined
    ),
    createdAt: row.createdAt,
    updatedAt: row.updatedAt,
  };
}

function parseJson<T>(value: string | null, fallback: T): T {
  if (!value) return fallback;
  try {
    return JSON.parse(value) as T;
  } catch {
    return fallback;
  }
}

function toStatus(value: string | null): "success" | "error" {
  return value === "error" ? "error" : "success";
}

function toSearchProvider(value: string | null): SearchProviderName | null {
  if (value === "serper" || value === "brave" || value === "tavily") {
    return value;
  }
  return null;
}
