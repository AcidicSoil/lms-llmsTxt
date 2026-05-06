import pino from "pino";
import fs from "node:fs";
import path from "node:path";
import { Writable } from "node:stream";
import type { NextRequest } from "next/server";
import type { Logger as PinoLogger } from "pino";

const SENSITIVE_KEY_PATTERN = /(key|token|secret|authorization|cookie)/i;
const MAX_STRING_LENGTH = 500;
const MAX_ARRAY_ITEMS = 25;
const MAX_OBJECT_KEYS = 100;

export type LogLevel = "debug" | "info" | "warn" | "error";
export type LogOutcome = "success" | "error";
export type LogEvent =
  | "api.generate.completed"
  | "api.models.completed"
  | "api.generate.exception"
  | "api.models.exception"
  | "api.generate.stage.started"
  | "api.generate.stage.succeeded"
  | "api.generate.stage.failed"
  | "search.provider.attempt"
  | "search.provider.selected"
  | "search.provider.exhausted"
  | "scrape.url.succeeded"
  | "scrape.batch.completed"
  | "scrape.url.failed"
  | "llm.models.fetch.completed"
  | "llm.models.fetch.failed"
  | "llm.generate.started"
  | "llm.generate.completed"
  | "llm.generate.failed"
  | "log.storage.init.failed"
  | "log.storage.rotate.completed"
  | "log.storage.rotate.failed"
  | "log.retention.sweep.completed"
  | "log.retention.sweep.failed"
  | "log.retention.file.deleted";

export type GenerationStage =
  | "request.parse"
  | "search.docs"
  | "scrape.urls"
  | "llm.models.fetch"
  | "llm.generate";

export interface RequestContext {
  requestId: string;
  method: string;
  path: string;
  route: string;
}

interface WideEventInput {
  event: Extract<LogEvent, "api.generate.completed" | "api.models.completed">;
  request: RequestContext;
  statusCode: number;
  outcome: LogOutcome;
  durationMs: number;
  metrics?: Record<string, unknown>;
  error?: {
    name?: string;
    message?: string;
    code?: string | number;
    stage?: string;
  };
}

type LogSinkMode = "stdout" | "file" | "dual";

interface LogStorageConfig {
  mode: LogSinkMode;
  level: string;
  dir: string;
  baseName: string;
  rotateMaxSizeBytes: number;
  retentionDays: number;
  retentionMaxFiles: number;
  retentionSweepIntervalMinutes: number;
}

interface LogFileEntry {
  name: string;
  fullPath: string;
  mtimeMs: number;
}

const loggerLevel = process.env.LOG_LEVEL?.trim() || "info";

function sanitizeKey(key: string, value: unknown): unknown {
  if (SENSITIVE_KEY_PATTERN.test(key)) {
    return "[REDACTED]";
  }
  return sanitizeForLogging(value);
}

export function sanitizeForLogging(value: unknown, depth = 0): unknown {
  if (value === null || value === undefined) return value;
  if (depth > 5) return "[TRUNCATED_DEPTH]";

  if (typeof value === "string") {
    if (value.length > MAX_STRING_LENGTH) {
      return `${value.slice(0, MAX_STRING_LENGTH)}...[TRUNCATED]`;
    }
    return value;
  }

  if (
    typeof value === "number" ||
    typeof value === "boolean" ||
    typeof value === "bigint"
  ) {
    return value;
  }

  if (value instanceof Error) {
    return {
      name: value.name,
      message: value.message,
    };
  }

  if (Array.isArray(value)) {
    const sliced = value
      .slice(0, MAX_ARRAY_ITEMS)
      .map((item) => sanitizeForLogging(item, depth + 1));
    if (value.length > MAX_ARRAY_ITEMS) {
      sliced.push(`[TRUNCATED_ITEMS:${value.length - MAX_ARRAY_ITEMS}]`);
    }
    return sliced;
  }

  if (typeof value === "object") {
    const entries = Object.entries(value as Record<string, unknown>).slice(
      0,
      MAX_OBJECT_KEYS
    );
    const output: Record<string, unknown> = {};
    for (const [key, current] of entries) {
      output[key] = sanitizeKey(key, sanitizeForLogging(current, depth + 1));
    }
    return output;
  }

  return String(value);
}

export function createRequestContext(
  req: NextRequest,
  route: string
): RequestContext {
  const headerValue = req.headers.get("x-request-id")?.trim();
  const requestId =
    headerValue && headerValue.length > 0 ? headerValue : crypto.randomUUID();

  return {
    requestId,
    method: req.method,
    path: req.nextUrl.pathname,
    route,
  };
}

export function logWideEvent(input: WideEventInput): void {
  logger.info({
    event: input.event,
    requestId: input.request.requestId,
    route: input.request.route,
    method: input.request.method,
    path: input.request.path,
    statusCode: input.statusCode,
    outcome: input.outcome,
    durationMs: input.durationMs,
    metrics: sanitizeForLogging(input.metrics ?? {}),
    error: sanitizeForLogging(input.error),
  });
}

export function logErrorEvent(
  event: Extract<LogEvent, "api.generate.exception" | "api.models.exception">,
  request: RequestContext,
  error: unknown,
  stage?: string
): void {
  logger.error({
    event,
    requestId: request.requestId,
    route: request.route,
    method: request.method,
    path: request.path,
    stage,
    error: sanitizeForLogging(error),
  });
}

export function logProgressEvent(input: {
  event: Extract<
    LogEvent,
    | "api.generate.stage.started"
    | "api.generate.stage.succeeded"
    | "api.generate.stage.failed"
  >;
  request: RequestContext;
  stage: GenerationStage;
  durationMs?: number;
  metrics?: Record<string, unknown>;
  error?: unknown;
}): void {
  logger.info({
    event: input.event,
    requestId: input.request.requestId,
    route: input.request.route,
    method: input.request.method,
    path: input.request.path,
    stage: input.stage,
    durationMs: input.durationMs,
    metrics: sanitizeForLogging(input.metrics ?? {}),
    error: sanitizeForLogging(input.error),
  });
}

function resolveLogStorageConfig(defaultLevel: string): LogStorageConfig {
  const modeRaw = process.env.LOG_SINK_MODE?.trim().toLowerCase();
  const mode: LogSinkMode =
    modeRaw === "file" || modeRaw === "dual" || modeRaw === "stdout"
      ? modeRaw
      : "dual";

  return {
    mode,
    level: defaultLevel,
    dir: resolveLogDir(process.env.LOG_DIR?.trim() || ".logs/hypergraph"),
    baseName: sanitizeBaseName(process.env.LOG_FILE_BASENAME?.trim() || "app"),
    rotateMaxSizeBytes:
      parsePositiveInt(process.env.LOG_ROTATE_MAX_SIZE_MB, 50) * 1024 * 1024,
    retentionDays: parsePositiveInt(process.env.LOG_RETENTION_DAYS, 14),
    retentionMaxFiles: parsePositiveInt(process.env.LOG_RETENTION_MAX_FILES, 20),
    retentionSweepIntervalMinutes: parsePositiveInt(
      process.env.LOG_RETENTION_SWEEP_INTERVAL_MIN,
      60
    ),
  };
}

function resolveLogDir(rawPath: string): string {
  if (path.isAbsolute(rawPath)) return rawPath;
  return path.resolve(process.cwd(), rawPath);
}

function parsePositiveInt(rawValue: string | undefined, fallback: number): number {
  const parsed = Number.parseInt(rawValue ?? "", 10);
  if (!Number.isFinite(parsed) || parsed <= 0) return fallback;
  return parsed;
}

function sanitizeBaseName(baseName: string): string {
  const cleaned = baseName.replace(/[^a-zA-Z0-9-_]/g, "-");
  return cleaned.length > 0 ? cleaned : "app";
}

function timestampForFilename(date: Date = new Date()): string {
  const pad = (v: number) => String(v).padStart(2, "0");
  return [
    date.getUTCFullYear(),
    pad(date.getUTCMonth() + 1),
    pad(date.getUTCDate()),
    "-",
    pad(date.getUTCHours()),
    pad(date.getUTCMinutes()),
    pad(date.getUTCSeconds()),
  ].join("");
}

class RotatingFileSink extends Writable {
  private readonly config: LogStorageConfig;
  private stream: fs.WriteStream | null = null;
  private bytesWritten = 0;
  private readonly currentPath: string;

  constructor(config: LogStorageConfig) {
    super({ decodeStrings: false });
    this.config = config;
    fs.mkdirSync(config.dir, { recursive: true });
    this.currentPath = path.join(config.dir, `${config.baseName}-current.ndjson`);

    if (fs.existsSync(this.currentPath)) {
      this.bytesWritten = fs.statSync(this.currentPath).size;
      if (this.bytesWritten >= this.config.rotateMaxSizeBytes) {
        this.rotateCurrentFile();
        this.bytesWritten = 0;
      }
    } else {
      this.bytesWritten = 0;
    }

    this.stream = fs.createWriteStream(this.currentPath, { flags: "a" });
  }

  _write(
    chunk: Buffer | string,
    _encoding: BufferEncoding,
    callback: (error?: Error | null) => void
  ): void {
    try {
    const line = typeof chunk === "string" ? chunk : chunk.toString("utf8");
    const nextSize = this.bytesWritten + Buffer.byteLength(line);

    if (nextSize >= this.config.rotateMaxSizeBytes && this.bytesWritten > 0) {
      this.rotateCurrentFile();
      this.bytesWritten = 0;
      this.stream = fs.createWriteStream(this.currentPath, { flags: "a" });
    }

    this.bytesWritten += Buffer.byteLength(line);
    if (this.stream) {
      this.stream.write(line);
    }
    callback();
    } catch (error) {
      callback(error instanceof Error ? error : new Error("log_write_failed"));
    }
  }

  currentFilePath(): string {
    return this.currentPath;
  }

  private rotateCurrentFile() {
    try {
      if (this.stream) {
        this.stream.end();
      }

      if (!fs.existsSync(this.currentPath)) return;

      const suffix = timestampForFilename();
      let sequence = 0;
      let rotatedPath = path.join(
        this.config.dir,
        `${this.config.baseName}-${suffix}.ndjson`
      );

      while (fs.existsSync(rotatedPath)) {
        sequence += 1;
        rotatedPath = path.join(
          this.config.dir,
          `${this.config.baseName}-${suffix}-${sequence}.ndjson`
        );
      }

      fs.renameSync(this.currentPath, rotatedPath);
    } catch {
      // Keep serving requests even if log rotation fails.
      process.stderr.write(
        JSON.stringify({
          level: 50,
          time: new Date().toISOString(),
          event: "log.storage.rotate.failed",
          path: this.currentPath,
        }) + "\n"
      );
    }
  }
}

function createRotatingFileSink(config: LogStorageConfig): RotatingFileSink | null {
  try {
    return new RotatingFileSink(config);
  } catch (error) {
    process.stderr.write(
      JSON.stringify({
        level: 50,
        time: new Date().toISOString(),
        event: "log.storage.init.failed",
        error: error instanceof Error ? error.message : "unknown_error",
      }) + "\n"
    );
    return null;
  }
}

function runRetentionSweep(
  config: LogStorageConfig,
  activeFilePath: string,
  activeLogger: PinoLogger
): void {
  try {
    const now = Date.now();
    const cutoff = now - config.retentionDays * 24 * 60 * 60 * 1000;
    const files = listManagedFiles(config);

    let deletedByAge = 0;
    for (const file of files) {
      if (file.fullPath === activeFilePath) continue;
      if (file.mtimeMs < cutoff) {
        fs.unlinkSync(file.fullPath);
        deletedByAge += 1;
        activeLogger.info({
          event: "log.retention.file.deleted",
          reason: "age",
          file: file.name,
        });
      }
    }

    const remaining = listManagedFiles(config).sort(
      (a, b) => a.mtimeMs - b.mtimeMs
    );
    const nonActive = remaining.filter((f) => f.fullPath !== activeFilePath);
    const overLimit = Math.max(0, remaining.length - config.retentionMaxFiles);
    let deletedByCount = 0;

    for (let i = 0; i < overLimit; i += 1) {
      const file = nonActive[i];
      if (!file) break;
      fs.unlinkSync(file.fullPath);
      deletedByCount += 1;
      activeLogger.info({
        event: "log.retention.file.deleted",
        reason: "count",
        file: file.name,
      });
    }

    activeLogger.info({
      event: "log.retention.sweep.completed",
      deletedByAge,
      deletedByCount,
      retentionDays: config.retentionDays,
      retentionMaxFiles: config.retentionMaxFiles,
    });
  } catch (error) {
    activeLogger.error({
      event: "log.retention.sweep.failed",
      error: error instanceof Error ? error.message : "unknown_error",
    });
  }
}

function listManagedFiles(config: LogStorageConfig): LogFileEntry[] {
  if (!fs.existsSync(config.dir)) return [];
  const files = fs.readdirSync(config.dir);
  const prefix = `${config.baseName}-`;
  return files
    .filter((file) => file.startsWith(prefix) && file.endsWith(".ndjson"))
    .map((file) => {
      const fullPath = path.join(config.dir, file);
      const stat = fs.statSync(fullPath);
      return {
        name: file,
        fullPath,
        mtimeMs: stat.mtimeMs,
      };
    });
}

function initializeLogger(): PinoLogger {
  const storageConfig = resolveLogStorageConfig(loggerLevel);
  const sink =
    storageConfig.mode === "file" || storageConfig.mode === "dual"
      ? createRotatingFileSink(storageConfig)
      : null;
  const streams: { stream: NodeJS.WritableStream }[] = [];

  if (storageConfig.mode === "stdout" || storageConfig.mode === "dual") {
    streams.push({ stream: process.stdout });
  }

  if (sink) {
    streams.push({ stream: sink });
  }

  if (streams.length === 0) {
    streams.push({ stream: process.stdout });
  }

  const initialized = pino(
    {
      level: storageConfig.level,
      base: {
        service: "hypergraph",
        nodeEnv: process.env.NODE_ENV ?? "development",
        appVersion: process.env.npm_package_version ?? "unknown",
        logSinkMode: storageConfig.mode,
      },
      timestamp: pino.stdTimeFunctions.isoTime,
    },
    streams.length === 1 ? streams[0].stream : pino.multistream(streams)
  );

  if (sink) {
    runRetentionSweep(storageConfig, sink.currentFilePath(), initialized);
    const intervalMs = storageConfig.retentionSweepIntervalMinutes * 60 * 1000;
    const timer = setInterval(() => {
      runRetentionSweep(storageConfig, sink.currentFilePath(), initialized);
    }, intervalMs);
    timer.unref();
  }

  return initialized;
}

export const logger: PinoLogger = initializeLogger();
