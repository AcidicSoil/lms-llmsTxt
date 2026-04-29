import OpenAI from "openai";
import type { GraphNode, SkillGraph, GeneratedFile } from "@/types/graph";
import { promises as fs } from "node:fs";
import { spawn } from "node:child_process";
import path from "node:path";

const openai = new OpenAI();

const SYSTEM_PROMPT = `You are a domain knowledge graph architect. Given a topic and source material, produce a deeply interconnected JSON skill graph that enables an agent to UNDERSTAND the domain — not merely summarize it. This is the difference between an agent that follows instructions and an agent that understands a domain.

Output format (JSON only):
{
  "topic": "the topic",
  "nodes": [
    {
      "id": "kebab-case-id",
      "label": "Human Readable Label",
      "type": "moc" | "concept" | "pattern" | "gotcha",
      "description": "One-sentence description the agent can scan to decide whether to read the full file",
      "content": "Full markdown content with [[wikilinks]] woven into prose",
      "links": ["other-node-id"]
    }
  ]
}

Node type definitions:
- "moc" — exactly 1 per graph; the Map of Content and traversal entry point
- "concept" — a foundational idea, theory, or framework in the domain
- "pattern" — a reusable approach, technique, or methodology
- "gotcha" — a counterintuitive finding, failure mode, or common mistake

Rules:
- Generate 12–18 nodes total
- Exactly 1 node must be type "moc"
- Every [[wikilink]] must appear INSIDE a prose sentence that explains WHY the agent should follow it. Never list wikilinks as bare bullets — they must carry meaning through the sentence they live in.
- The "links" array must list every node ID referenced via [[wikilinks]] in the content
- Every non-moc node must begin with YAML frontmatter:
  ---
  title: Human Readable Label
  type: concept | pattern | gotcha
  description: One-sentence scan description
  ---
- Node IDs must be kebab-case
- Content must be rich, substantive markdown — not summaries. Each node is one complete thought or claim about the domain.

MOC node requirements (type "moc"):
- Opens with a 2-3 sentence overview of the domain and why structured knowledge of it matters
- Contains a "## Domain Clusters" section where each cluster is described in 1-2 sentences with [[wikilinks]] to relevant concept nodes woven into the prose
- Contains an "## Explorations Needed" section with 2-3 open questions the graph does not yet answer — gaps in the current knowledge structure
- The MOC is a navigable entry point, not a table of contents. Each link must be justified in prose.

Depth requirements:
- Concept nodes must explain the underlying mechanism or theory, not just define terms
- Pattern nodes must include when to apply the pattern and what breaks it
- Gotcha nodes must explain why the mistake is made and what the correct mental model is
- This graph should give an agent enough structured knowledge to reason about novel situations in the domain`;

export async function generateGraph(
  topic: string,
  docs: { url: string; markdown: string }[],
): Promise<{ graph: SkillGraph; files: GeneratedFile[] }> {
  const truncatedDocs = docs
    .map((d) => `## Source: ${d.url}\n\n${d.markdown.slice(0, 4000)}`)
    .join("\n\n---\n\n");

  const response = await openai.chat.completions.create({
    model: "gpt-4o",
    response_format: { type: "json_object" },
    messages: [
      { role: "system", content: SYSTEM_PROMPT },
      {
        role: "user",
        content: `Topic: ${topic}\n\nScraped documentation:\n\n${truncatedDocs}`,
      },
    ],
    temperature: 0.7,
    max_tokens: 8192,
  });

  const raw = response.choices[0].message.content;
  if (!raw) throw new Error("Empty response from OpenAI");

  const parsed = JSON.parse(raw) as SkillGraph;

  if (!parsed.nodes || parsed.nodes.length < 3) {
    throw new Error("Generated graph has too few nodes");
  }

  const files: GeneratedFile[] = parsed.nodes.map((node: GraphNode) => ({
    path: `${slugify(topic)}/${node.id}.md`,
    content: node.content,
  }));

  return { graph: parsed, files };
}

function resolveRepoGraphPath(graphPath: string): string {
  const absolute = path.isAbsolute(graphPath)
    ? graphPath
    : path.resolve(process.cwd(), graphPath);
  const artifactsRoot = path.resolve(process.cwd(), "..", "artifacts");
  if (!absolute.startsWith(`${artifactsRoot}${path.sep}`)) {
    throw new Error("Graph path must be within the artifacts directory");
  }
  return absolute;
}

export async function loadRepoGraph(
  graphPath: string,
): Promise<{ graph: SkillGraph; files: GeneratedFile[] }> {
  const absolute = resolveRepoGraphPath(graphPath);
  const raw = await fs.readFile(absolute, "utf-8");
  const parsed = JSON.parse(raw) as SkillGraph;
  if (!parsed.nodes || parsed.nodes.length === 0) {
    throw new Error("Graph file is missing nodes");
  }
  const files: GeneratedFile[] = parsed.nodes.map((node: GraphNode) => ({
    path: `${slugify(parsed.topic || "repo")}/${node.id}.md`,
    content: node.content,
  }));
  return { graph: parsed, files };
}

function parseGithubRepoUrl(repoUrl: string): { owner: string; repo: string } {
  let parsed: URL;
  try {
    parsed = new URL(repoUrl);
  } catch {
    throw new Error("Repository URL must be a valid URL");
  }
  if (parsed.hostname !== "github.com") {
    throw new Error("Repository URL must be a github.com URL");
  }
  const parts = parsed.pathname.replace(/^\/+|\/+$/g, "").split("/");
  if (parts.length < 2 || !parts[0] || !parts[1]) {
    throw new Error("Repository URL must be https://github.com/<owner>/<repo>");
  }
  return {
    owner: parts[0],
    repo: parts[1].replace(/\.git$/i, ""),
  };
}

async function runCommand(
  cmd: string,
  args: string[],
  options: { cwd: string; env?: NodeJS.ProcessEnv },
): Promise<{ stdout: string; stderr: string }> {
  return new Promise((resolve, reject) => {
    const child = spawn(cmd, args, {
      cwd: options.cwd,
      env: options.env,
      stdio: ["ignore", "pipe", "pipe"],
    });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk) => {
      stdout += String(chunk);
    });
    child.stderr.on("data", (chunk) => {
      stderr += String(chunk);
    });
    child.on("error", (error) => reject(error));
    child.on("close", (code) => {
      if (code === 0) {
        resolve({ stdout, stderr });
        return;
      }
      const detail = (stderr || stdout).trim().split("\n").slice(-8).join("\n");
      reject(
        new Error(
          `lmstxt CLI failed (exit ${code})${detail ? `:\n${detail}` : ""}`,
        ),
      );
    });
  });
}

function buildPythonEnv(repoRoot: string): NodeJS.ProcessEnv {
  const env = { ...process.env };
  const repoSrc = path.join(repoRoot, "src");
  env.PYTHONPATH = env.PYTHONPATH
    ? `${repoSrc}${path.delimiter}${env.PYTHONPATH}`
    : repoSrc;
  return env;
}

async function runLocalLmstxt(
  repoRoot: string,
  repoUrl: string,
): Promise<void> {
  const artifactsDir = path.join(repoRoot, "artifacts");
  const env = buildPythonEnv(repoRoot);
  const pythonCandidates = [
    process.env.LMSTXT_PYTHON_BIN,
    "python3",
    "python",
  ].filter((value): value is string => Boolean(value && value.trim()));
  let lastError: Error | null = null;

  for (const pythonBin of pythonCandidates) {
    try {
      await runCommand(
        pythonBin,
        [
          "-m",
          "lms_llmsTxt.cli",
          repoUrl,
          "--generate-graph",
          "--graph-only",
          "--output-dir",
          artifactsDir,
        ],
        { cwd: repoRoot, env },
      );
      return;
    } catch (error) {
      lastError = error instanceof Error ? error : new Error(String(error));
    }
  }

  throw lastError ?? new Error("Unable to execute local lmstxt CLI");
}

export async function generateRepoGraph(
  repoUrl: string,
): Promise<{
  graph: SkillGraph;
  files: GeneratedFile[];
  artifactPath: string;
}> {
  const { owner, repo } = parseGithubRepoUrl(repoUrl);
  const hypergraphDir = process.cwd();
  const repoRoot = path.resolve(hypergraphDir, "..");
  await runLocalLmstxt(repoRoot, repoUrl);

  const graphPath = path.join(
    "..",
    "artifacts",
    owner,
    repo,
    "graph",
    "repo.graph.json",
  );
  const loaded = await loadRepoGraph(graphPath);
  return { ...loaded, artifactPath: graphPath };
}

function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
}
