import { defineConfig } from "drizzle-kit";

const rawDatabaseUrl = process.env.DATABASE_URL ?? "file:./data/hypergraph.db";
const databaseUrl = rawDatabaseUrl.startsWith("file:")
  ? rawDatabaseUrl.slice("file:".length)
  : rawDatabaseUrl;

export default defineConfig({
  schema: "./lib/db/schema.ts",
  out: "./drizzle",
  dialect: "sqlite",
  dbCredentials: {
    url: databaseUrl,
  },
});
