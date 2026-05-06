import { index, integer, sqliteTable, text } from "drizzle-orm/sqlite-core";

export const generations = sqliteTable(
  "generations",
  {
    id: text("id").primaryKey(),
    createdAt: integer("created_at").notNull(),
    updatedAt: integer("updated_at").notNull(),
    requestId: text("request_id").notNull(),
    topic: text("topic").notNull(),
    model: text("model"),
    status: text("status").notNull(),
    searchProvider: text("search_provider"),
    searchAttemptsJson: text("search_attempts_json"),
    graphJson: text("graph_json").notNull(),
    filesJson: text("files_json").notNull(),
    metricsJson: text("metrics_json"),
    errorJson: text("error_json"),
  },
  (table) => ({
    createdAtIdx: index("idx_generations_created_at").on(table.createdAt),
    topicIdx: index("idx_generations_topic").on(table.topic),
    requestIdIdx: index("idx_generations_request_id").on(table.requestId),
    statusIdx: index("idx_generations_status").on(table.status),
  })
);

export type GenerationRow = typeof generations.$inferSelect;
export type NewGenerationRow = typeof generations.$inferInsert;
