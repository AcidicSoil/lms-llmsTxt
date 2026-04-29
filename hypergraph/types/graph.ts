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

export interface GenerateResponse {
  graph: SkillGraph;
  files: GeneratedFile[];
  artifactPath?: string;
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
