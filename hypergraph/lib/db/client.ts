import fs from "node:fs";
import path from "node:path";
import Database from "better-sqlite3";
import { drizzle, type BetterSQLite3Database } from "drizzle-orm/better-sqlite3";
import * as schema from "@/lib/db/schema";

type DB = BetterSQLite3Database<typeof schema>;

declare global {
  var __hypergraphDb: DB | undefined;
  var __hypergraphSqlite: Database.Database | undefined;
}

function resolveDatabasePath(): string {
  const raw = process.env.DATABASE_URL?.trim() || "file:./data/hypergraph.db";
  if (raw.startsWith("file:")) {
    return path.resolve(process.cwd(), raw.slice("file:".length));
  }
  return path.resolve(process.cwd(), raw);
}

function ensureDatabaseSchema(sqlite: Database.Database): void {
  sqlite.exec(`
    CREATE TABLE IF NOT EXISTS generations (
      id TEXT PRIMARY KEY NOT NULL,
      created_at INTEGER NOT NULL,
      updated_at INTEGER NOT NULL,
      request_id TEXT NOT NULL,
      topic TEXT NOT NULL,
      model TEXT,
      status TEXT NOT NULL,
      search_provider TEXT,
      search_attempts_json TEXT,
      graph_json TEXT NOT NULL,
      files_json TEXT NOT NULL,
      metrics_json TEXT,
      error_json TEXT
    );
  `);

  sqlite.exec(
    "CREATE INDEX IF NOT EXISTS idx_generations_created_at ON generations(created_at);"
  );
  sqlite.exec(
    "CREATE INDEX IF NOT EXISTS idx_generations_topic ON generations(topic);"
  );
  sqlite.exec(
    "CREATE INDEX IF NOT EXISTS idx_generations_request_id ON generations(request_id);"
  );
  sqlite.exec(
    "CREATE INDEX IF NOT EXISTS idx_generations_status ON generations(status);"
  );
}

export function getDb(): DB {
  if (globalThis.__hypergraphDb && globalThis.__hypergraphSqlite) {
    return globalThis.__hypergraphDb;
  }

  const dbFilePath = resolveDatabasePath();
  fs.mkdirSync(path.dirname(dbFilePath), { recursive: true });

  const sqlite = new Database(dbFilePath);
  sqlite.pragma("journal_mode = WAL");
  ensureDatabaseSchema(sqlite);

  const db = drizzle(sqlite, { schema });

  globalThis.__hypergraphSqlite = sqlite;
  globalThis.__hypergraphDb = db;

  return db;
}
