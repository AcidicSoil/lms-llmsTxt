export type NodeType = "moc" | "concept" | "pattern" | "gotcha";

export interface GraphNode {
  id: string;
  label: string;
  type: NodeType;
  description: string;
  content: string;
  links: string[];
  evidence?: Array<{
    path: string;
    start_line?: number;
    end_line?: number;
    artifact_ref?: string;
    excerpt?: string;
  }>;
}

export interface SkillGraph {
  topic: string;
  nodes: GraphNode[];
}

export interface GeneratedFile {
  path: string;
  content: string;
}

export interface GenerateTrace {
  requestId: string;
  mode: "topic" | "generate-repo-graph" | "load-repo-graph";
  provider?: string;
  model?: string;
  durationMs?: number;
  promptSourceCount?: number;
  promptInputChars?: number;
  completionTokens?: number;
  promptTokens?: number;
  totalTokens?: number;
  finishReason?: string | null;
  pythonBin?: string;
}

export interface GenerateResponse {
  graph: SkillGraph;
  files: GeneratedFile[];
  artifactPath?: string;
  requestId?: string;
  trace?: GenerateTrace;
  meta?: {
    generationId?: string;
    requestId?: string;
    persistenceWarning?: "store_failed";
    model?: string;
    searchProvider?: "serper" | "brave" | "tavily";
    searchAttempts?: Array<{
      provider: "serper" | "brave" | "tavily";
      ok: boolean;
      reason?: string;
      resultCount?: number;
    }>;
  };
}

export interface GenerationRecordSummary {
  id: string;
  topic: string;
  model: string | null;
  status: "success" | "error";
  requestId: string;
  searchProvider: "serper" | "brave" | "tavily" | null;
  nodeCount: number;
  fileCount: number;
  createdAt: number;
}

export interface GenerationRecordDetail {
  id: string;
  topic: string;
  model: string | null;
  status: "success" | "error";
  requestId: string;
  searchProvider: "serper" | "brave" | "tavily" | null;
  searchAttempts: Array<{
    provider: "serper" | "brave" | "tavily";
    ok: boolean;
    reason?: string;
    resultCount?: number;
  }>;
  graph: SkillGraph;
  files: GeneratedFile[];
  metrics?: Record<string, unknown>;
  error?: Record<string, unknown>;
  createdAt: number;
  updatedAt: number;
}

export interface GenerationsListResponse {
  generations: GenerationRecordSummary[];
}

export interface ModelOption {
  id: string;
  label: string;
}

export interface ModelsResponse {
  models: ModelOption[];
  error?: string;
}

export interface ForceGraphNode {
  id: string;
  label: string;
  type: NodeType;
  val: number;
}

export interface ForceGraphLink {
  source: string;
  target: string;
}

export interface ForceGraphData {
  nodes: ForceGraphNode[];
  links: ForceGraphLink[];
}

export const NODE_COLORS: Record<NodeType, string> = {
  moc: "#000000",
  concept: "#404040",
  pattern: "#737373",
  gotcha: "#a3a3a3",
};

export const NODE_SIZES: Record<NodeType, number> = {
  moc: 3,
  concept: 2,
  pattern: 1.5,
  gotcha: 1,
};
