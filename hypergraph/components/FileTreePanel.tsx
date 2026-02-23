"use client";

import { useState } from "react";
import type { GeneratedFile, SkillGraph, NodeType } from "@/types/graph";

interface FileTreePanelProps {
  files: GeneratedFile[];
  graph: SkillGraph;
  selectedNodeId: string | null;
  onSelect: (nodeId: string) => void;
}

const TYPE_DOT: Record<NodeType, string> = {
  moc:     "bg-zinc-900",
  concept: "bg-zinc-600",
  pattern: "bg-zinc-400",
  gotcha:  "border border-zinc-300 bg-white",
};

function toNodeId(filePath: string): string {
  // e.g. "cbt-therapy/cognitive-distortions.md" → "cognitive-distortions"
  const name = filePath.split("/").pop() ?? filePath;
  return name.replace(/\.md$/, "");
}

export default function FileTreePanel({
  files,
  graph,
  selectedNodeId,
  onSelect,
}: FileTreePanelProps) {
  const [folderOpen, setFolderOpen] = useState(true);

  const topicSlug = graph.topic
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");

  // Sort: moc first, then alphabetical
  const sortedFiles = [...files].sort((a, b) => {
    const aId = toNodeId(a.path);
    const bId = toNodeId(b.path);
    const aNode = graph.nodes.find((n) => n.id === aId);
    const bNode = graph.nodes.find((n) => n.id === bId);
    if (aNode?.type === "moc") return -1;
    if (bNode?.type === "moc") return 1;
    return aId.localeCompare(bId);
  });

  return (
    <div className="flex h-full w-[200px] flex-shrink-0 flex-col overflow-hidden border-r border-zinc-200 bg-white">
      {/* Panel header */}
      <div className="flex flex-shrink-0 items-center border-b border-zinc-200 px-3 py-2">
        <span
          className="text-[10px] font-semibold uppercase tracking-widest text-zinc-400"
          style={{ letterSpacing: "0.08em" }}
        >
          Explorer
        </span>
      </div>

      {/* Tree */}
      <div className="flex-1 overflow-y-auto py-1">
        {/* Folder row */}
        <button
          onClick={() => setFolderOpen((o) => !o)}
          className="flex w-full items-center gap-1.5 px-2 py-1 text-left transition-colors hover:bg-zinc-50"
        >
          {/* Chevron */}
          <svg
            className={`h-3 w-3 flex-shrink-0 text-zinc-400 transition-transform duration-150 ${folderOpen ? "rotate-90" : ""}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2.5}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
          </svg>
          {/* Folder icon */}
          <svg
            className="h-3.5 w-3.5 flex-shrink-0 text-zinc-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.75}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M2.25 12.75V12A2.25 2.25 0 014.5 9.75h15A2.25 2.25 0 0121.75 12v.75m-8.69-6.44l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v8.25"
            />
          </svg>
          <span
            className="flex-1 truncate font-mono text-[11px] text-zinc-600"
            title={topicSlug}
          >
            {topicSlug}
          </span>
          {/* Count badge */}
          <span className="ml-auto flex-shrink-0 rounded-full bg-zinc-100 px-1.5 py-px font-mono text-[9px] text-zinc-400">
            {files.length}
          </span>
        </button>

        {/* File rows */}
        {folderOpen && (
          <div>
            {sortedFiles.map((file) => {
              const nodeId = toNodeId(file.path);
              const node = graph.nodes.find((n) => n.id === nodeId);
              const isActive = nodeId === selectedNodeId;
              const fileName = (file.path.split("/").pop() ?? file.path);

              return (
                <button
                  key={file.path}
                  onClick={() => onSelect(nodeId)}
                  title={node?.description ?? fileName}
                  className={`flex w-full items-center gap-2 py-[5px] pl-7 pr-2 text-left transition-colors duration-100 ${
                    isActive
                      ? "bg-zinc-100 text-zinc-900"
                      : "text-zinc-500 hover:bg-zinc-50 hover:text-zinc-800"
                  }`}
                >
                  {/* Type dot */}
                  <span
                    className={`h-1.5 w-1.5 flex-shrink-0 rounded-full ${node ? TYPE_DOT[node.type] : "bg-zinc-300"}`}
                  />
                  {/* File name */}
                  <span
                    className={`flex-1 truncate font-mono text-[11px] ${isActive ? "font-semibold" : ""}`}
                    style={{ letterSpacing: "0" }}
                  >
                    {fileName}
                  </span>
                </button>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
