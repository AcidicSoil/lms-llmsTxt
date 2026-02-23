"use client";

import { useState } from "react";
import JSZip from "jszip";
import TopicInput from "@/components/TopicInput";
import GraphView from "@/components/GraphView";
import NodePreview from "@/components/NodePreview";
import FileTreePanel from "@/components/FileTreePanel";
import type {
  SkillGraph,
  GeneratedFile,
  GenerateResponse,
  ForceGraphData,
  GraphNode,
} from "@/types/graph";
import { NODE_SIZES } from "@/types/graph";

const EXAMPLE_TOPICS = [
  "Supabase Auth",
  "React Server Components",
  "Postgres Optimization",
  "TypeScript Type System",
  "Vercel AI SDK",
  "Docker Networking",
];

function buildForceGraphData(graph: SkillGraph): ForceGraphData {
  const nodeIds = new Set(graph.nodes.map((n) => n.id));
  const linkSet = new Set<string>();
  const links: ForceGraphData["links"] = [];

  for (const node of graph.nodes) {
    for (const target of node.links) {
      if (!nodeIds.has(target)) continue;
      const key = [node.id, target].sort().join("::");
      if (!linkSet.has(key)) {
        linkSet.add(key);
        links.push({ source: node.id, target });
      }
    }
  }

  return {
    nodes: graph.nodes.map((n) => ({
      id: n.id,
      label: n.label,
      type: n.type,
      val: NODE_SIZES[n.type] + Math.min(n.links.length * 0.5, 4),
    })),
    links,
  };
}

interface AppError {
  message: string;
  isPlanLimit?: boolean;
  upgradeUrl?: string;
}

export default function Home() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<AppError | null>(null);
  const [graph, setGraph] = useState<SkillGraph | null>(null);
  const [files, setFiles] = useState<GeneratedFile[]>([]);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [submittedTopic, setSubmittedTopic] = useState<string>("");

  const selectedNode: GraphNode | null =
    graph?.nodes.find((n) => n.id === selectedNodeId) ?? null;

  const graphData = graph ? buildForceGraphData(graph) : null;
  const hasResults = isLoading || !!graphData || !!error;

  async function handleSubmit(topic: string) {
    setSubmittedTopic(topic);
    setIsLoading(true);
    setError(null);
    setGraph(null);
    setFiles([]);
    setSelectedNodeId(null);

    try {
      const res = await fetch("/api/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic }),
      });

      const data: GenerateResponse & {
        error?: string;
        upgradeUrl?: string;
        hint?: string;
      } = await res.json();

      if (res.status === 402) {
        setError({
          message: data.error ?? "Concurrency limit reached",
          isPlanLimit: true,
          upgradeUrl: data.upgradeUrl ?? "https://hyperbrowser.ai",
        });
        return;
      }

      if (!res.ok || data.error) {
        setError({ message: data.error ?? "Generation failed" });
        return;
      }

      setGraph(data.graph);
      setFiles(data.files);

      const indexNode = data.graph.nodes.find((n) => n.type === "moc");
      if (indexNode) {
        setSelectedNodeId(indexNode.id);
      }
    } catch (err) {
      setError({
        message: err instanceof Error ? err.message : "Something went wrong",
      });
    } finally {
      setIsLoading(false);
    }
  }

  async function handleDownload() {
    if (!graph || files.length === 0) return;
    const zip = new JSZip();
    const folder = graph.topic.toLowerCase().replace(/[^a-z0-9]+/g, "-");

    for (const file of files) {
      zip.file(file.path, file.content);
    }

    const mocNode = graph.nodes.find((n) => n.type === "moc");
    const readme = [
      `# ${graph.topic} Skill Graph`,
      ``,
      `**Built with [HyperGraph](https://hyperbrowser.ai)**`,
      ``,
      `A traversable knowledge graph of **${graph.nodes.length} interconnected nodes** covering the ${graph.topic} domain.`,
      ``,
      `## Usage with Claude Code / Cursor`,
      ``,
      `Copy this folder into your \`.claude/skills/\` or \`.cursor/skills/\` directory.`,
      `Point your agent at \`${folder}/${mocNode?.id ?? "moc"}.md\` as the entry point.`,
      ``,
      `Each node is one complete thought. Follow [[wikilinks]] to traverse the domain.`,
      `Your agent will navigate the graph — pulling in exactly what the current situation requires.`,
      ``,
      `## Node Types`,
      ``,
      `- **MOC** — Map of Content; the entry point and domain overview`,
      `- **Concept** — foundational ideas, theories, and frameworks`,
      `- **Pattern** — reusable approaches and techniques`,
      `- **Gotcha** — failure modes, counterintuitive findings, common mistakes`,
      ``,
      `## Nodes`,
      ``,
      ...graph.nodes.map((n) => `- \`${n.id}.md\` — ${n.description}`),
      ``,
      `---`,
      `Follow [@hyperbrowser](https://hyperbrowser.ai) for updates.`,
    ].join("\n");

    zip.file(`${folder}/README.md`, readme);

    const blob = await zip.generateAsync({ type: "blob" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${folder}.zip`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function handleWikilinkClick(nodeId: string) {
    if (graph?.nodes.some((n) => n.id === nodeId)) {
      setSelectedNodeId(nodeId);
    }
  }

  /* ── Landing screen ── */
  if (!hasResults) {
    return (
      <div className="flex h-screen flex-col bg-white font-sans">
        {/* Top nav */}
        <nav className="flex flex-shrink-0 items-center justify-between border-b border-zinc-100 px-5 py-3">
          <a href="https://hyperbrowser.ai" target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 transition-opacity hover:opacity-70">
            <svg width="12" height="20" viewBox="0 0 104 167" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M76.4409 0.958618L0.27832 83.6963H41.5624C47.8498 83.6963 53.3845 79.5487 55.1561 73.5091L76.4409 0.958618Z" fill="#1D1D1D"/>
              <path d="M48.9596 93.881L27.6748 166.434L103.837 83.6959H62.5532C56.2659 83.6959 50.7312 87.8436 48.9596 93.8831V93.881Z" fill="#1D1D1D"/>
            </svg>
            <span className="text-[11px] font-semibold text-zinc-400" style={{ letterSpacing: "0.01em" }}>Hyperbrowser</span>
          </a>
          <a
            href="https://hyperbrowser.ai"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 rounded-md border border-zinc-200 px-3 py-1.5 text-[11px] font-semibold text-zinc-600 transition-all duration-150 hover:border-zinc-900 hover:bg-zinc-900 hover:text-white active:scale-95"
          >
            <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
              <circle cx="7.5" cy="15.5" r="5.5" />
              <path d="M21 2l-9.6 9.6M15.5 7.5l2 2" />
            </svg>
            Get API Key
          </a>
        </nav>

        {/* Centered content */}
        <div className="flex flex-1 flex-col items-center justify-center px-4">
          <div className="w-full max-w-2xl">
            {/* Brand */}
            <div className="mb-8 text-center">
              <h1
                className="text-4xl font-bold text-zinc-900"
                style={{ letterSpacing: "-0.04em" }}
              >
                Hyper<span className="font-extralight">Graph</span>
              </h1>
              <p className="accent mt-2.5 text-xs font-semibold text-zinc-400">
                Give your agent a domain to understand, not just instructions to follow
              </p>
            </div>

            {/* Hero input */}
            <TopicInput
              onSubmit={handleSubmit}
              isLoading={isLoading}
              variant="hero"
            />

            {/* Example chips */}
            <div className="mt-4 flex flex-wrap justify-center gap-2">
              {EXAMPLE_TOPICS.map((t) => (
                <button
                  key={t}
                  onClick={() => handleSubmit(t)}
                  className="accent rounded-full border border-zinc-200 px-3 py-1.5 text-[10px] font-semibold text-zinc-500 transition-all duration-150 hover:border-zinc-900 hover:bg-zinc-900 hover:text-white active:scale-95"
                >
                  {t}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <p className="accent pb-6 text-center text-[10px] font-semibold text-zinc-300">
          Powered by Hyperbrowser
        </p>
      </div>
    );
  }

  /* ── Results / loading screen ── */
  return (
    <div className="flex h-screen flex-col bg-white font-sans text-zinc-900">
      {/* Compact header */}
      <header className="flex flex-shrink-0 items-center gap-3 border-b border-zinc-200 px-5 py-2.5">
        {/* Logo + brand */}
        <button
          onClick={() => {
            setGraph(null);
            setFiles([]);
            setError(null);
            setSelectedNodeId(null);
            setSubmittedTopic(""); 
          }}
          className="flex flex-shrink-0 items-center gap-2 transition-opacity hover:opacity-60"
        >
          <svg width="10" height="16" viewBox="0 0 104 167" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M76.4409 0.958618L0.27832 83.6963H41.5624C47.8498 83.6963 53.3845 79.5487 55.1561 73.5091L76.4409 0.958618Z" fill="#1D1D1D"/>
            <path d="M48.9596 93.881L27.6748 166.434L103.837 83.6959H62.5532C56.2659 83.6959 50.7312 87.8436 48.9596 93.8831V93.881Z" fill="#1D1D1D"/>
          </svg>
          <span
            className="font-bold text-zinc-900"
            style={{ letterSpacing: "-0.03em", fontSize: "15px" }}
          >
            Hyper<span className="font-extralight">Graph</span>
          </span>
        </button>
        <div className="h-4 w-px bg-zinc-200" />
        <div className="flex-1">
          <TopicInput
            onSubmit={handleSubmit}
            isLoading={isLoading}
            variant="compact"
            initialValue={submittedTopic}
          />
        </div>
        {files.length > 0 && (
          <button
            onClick={handleDownload}
            className="flex flex-shrink-0 items-center gap-1.5 rounded-md border border-zinc-300 px-3 py-1.5 text-xs font-medium text-zinc-700 transition-all duration-150 hover:border-zinc-900 hover:bg-zinc-900 hover:text-white active:scale-95"
          >
            <svg
              className="h-3.5 w-3.5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
              />
            </svg>
            Download .zip
          </button>
        )}
        <div className="h-4 w-px bg-zinc-200 flex-shrink-0" />
        <a
          href="https://hyperbrowser.ai"
          target="_blank"
          rel="noopener noreferrer"
          className="flex flex-shrink-0 items-center gap-1.5 rounded-md border border-zinc-200 px-3 py-1.5 text-[11px] font-semibold text-zinc-600 transition-all duration-150 hover:border-zinc-900 hover:bg-zinc-900 hover:text-white active:scale-95"
        >
          <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
            <circle cx="7.5" cy="15.5" r="5.5" />
            <path d="M21 2l-9.6 9.6M15.5 7.5l2 2" />
          </svg>
          Get API Key
        </a>
      </header>

      {/* Error bar */}
      {error && !error.isPlanLimit && (
        <div className="flex items-center gap-2 border-b border-red-100 bg-red-50 px-5 py-2.5 text-sm text-red-700">
          <svg
            className="h-4 w-4 flex-shrink-0"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
            />
          </svg>
          {error.message}
        </div>
      )}

      {/* Plan limit banner */}
      {error?.isPlanLimit && (
        <div className="flex items-center justify-between gap-3 border-b border-amber-200 bg-amber-50 px-5 py-3">
          <div className="flex items-start gap-2.5">
            <svg
              className="mt-0.5 h-4 w-4 flex-shrink-0 text-amber-600"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
              />
            </svg>
            <div>
              <p className="text-xs font-semibold text-amber-800">
                Free plan — concurrent browser limit reached
              </p>
              <p className="mt-0.5 text-[11px] text-amber-700">
                Your Hyperbrowser plan supports only 1 concurrent browser session. Upgrade to run parallel scrapes.
              </p>
            </div>
          </div>
          <a
            href={error.upgradeUrl ?? "https://hyperbrowser.ai"}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-shrink-0 rounded-md bg-amber-800 px-3 py-1.5 text-[11px] font-semibold text-white transition-opacity hover:opacity-80"
          >
            Upgrade plan
          </a>
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="flex flex-1 flex-col items-center justify-center gap-5">
          <div className="relative h-10 w-10">
            <svg
              className="h-10 w-10 text-zinc-100"
              viewBox="0 0 24 24"
              fill="none"
            >
              <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" />
            </svg>
            <svg
              className="absolute inset-0 h-10 w-10 animate-spin text-zinc-900"
              style={{ animationDuration: "0.75s" }}
              viewBox="0 0 24 24"
              fill="none"
            >
              <path
                d="M12 2a10 10 0 0110 10"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              />
            </svg>
          </div>
          <div className="text-center">
            <p className="text-sm font-bold text-zinc-900" style={{ letterSpacing: "-0.02em" }}>
              Building{submittedTopic ? ` "${submittedTopic}"` : ""} graph
            </p>
            <p className="accent mt-1.5 text-[10px] font-semibold text-zinc-400">
              Mapping the knowledge structure for this domain
            </p>
          </div>
        </div>
      )}

      {/* Graph + Preview */}
      {!isLoading && graphData && graph && (
        <main className="flex flex-1 overflow-hidden">
          <FileTreePanel
            files={files}
            graph={graph}
            selectedNodeId={selectedNodeId}
            onSelect={setSelectedNodeId}
          />
          <div className="flex-1 border-r border-zinc-200 overflow-hidden">
            <GraphView
              data={graphData}
              onNodeClick={setSelectedNodeId}
              selectedNodeId={selectedNodeId}
            />
          </div>
          <div className="w-[380px] flex-shrink-0">
            <NodePreview
              node={selectedNode}
              onWikilinkClick={handleWikilinkClick}
            />
          </div>
        </main>
      )}
    </div>
  );
}
