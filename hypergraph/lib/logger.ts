import pino from "pino";

export const logger = pino({
  name: "hypergraph",
  level: process.env.HYPERGRAPH_LOG_LEVEL ?? "info",
});

export function errorToLog(error: unknown): { type: string; message: string } {
  if (error instanceof Error) {
    return { type: error.name, message: error.message };
  }
  return { type: typeof error, message: String(error) };
}

export function preview(value: string, maxLength = 120): string {
  return value.length > maxLength ? `${value.slice(0, maxLength)}…` : value;
}
