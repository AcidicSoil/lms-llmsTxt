"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { GraphNode, NodeType } from "@/types/graph";
import type { ReactNode } from "react";
import React, { useState } from "react";

interface NodePreviewProps {
  node: GraphNode | null;
  onWikilinkClick: (nodeId: string) => void;
}

const TYPE_STYLES: Record<NodeType, string> = {
  moc:     "bg-zinc-900 text-white border-zinc-900",
  concept: "bg-zinc-700 text-white border-zinc-700",
  pattern: "bg-zinc-400 text-white border-zinc-400",
  gotcha:  "border-zinc-300 text-zinc-500 bg-zinc-50",
};

function toSlug(label: string): string {
  return label
    .toLowerCase()
    .replace(/\s+/g, "-")
    .replace(/[^a-z0-9-]/g, "");
}

function CopyButton({ text, label = "Copy" }: { text: string; label?: string }) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    await navigator.clipboard.writeText(String(text));
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  }

  return (
    <button
      onClick={handleCopy}
      className="flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium text-zinc-400 transition-all duration-150 hover:bg-zinc-200 hover:text-zinc-700 active:scale-95"
    >
      {copied ? (
        <>
          <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
          </svg>
          Copied
        </>
      ) : (
        <>
          <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.666 3.888A2.25 2.25 0 0013.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 01-.75.75H9a.75.75 0 01-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 01-2.25 2.25H6.75A2.25 2.25 0 014.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 011.927-.184" />
          </svg>
          {label}
        </>
      )}
    </button>
  );
}

export default function NodePreview({
  node,
  onWikilinkClick,
}: NodePreviewProps) {
  if (!node) {
    return (
      <div className="flex h-full items-center justify-center bg-zinc-50">
        <div className="text-center">
          <svg
            className="mx-auto mb-3 h-9 w-9 text-zinc-200"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.25}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
            />
          </svg>
          <p className="text-xs text-zinc-400">Select a node to view content</p>
        </div>
      </div>
    );
  }

  const slug = toSlug(node.label);

  function processWikilinks(text: string): ReactNode[] {
    const parts = text.split(/(\[\[[^\]]+\]\])/g);
    return parts.map((part, i) => {
      const match = part.match(/^\[\[([^\]]+)\]\]$/);
      if (match) {
        const linkId = match[1];
        return (
          <button
            key={i}
            onClick={() => onWikilinkClick(linkId)}
            className="mx-0.5 inline-block rounded border border-zinc-300 px-1.5 py-0.5 text-xs font-semibold text-zinc-700 transition-all duration-100 hover:border-zinc-900 hover:bg-zinc-900 hover:text-white active:scale-95"
            style={{ letterSpacing: "-0.01em" }}
          >
            {linkId}
          </button>
        );
      }
      return <React.Fragment key={i}>{part}</React.Fragment>;
    });
  }

  return (
    <div className="flex h-full flex-col overflow-hidden bg-white">

      {/* ── Editor tab strip ─────────────────────────────────────────────── */}
      <div className="flex flex-shrink-0 items-stretch border-b border-zinc-200 bg-[#f3f3f3]">
        {/* Active tab */}
        <div className="flex min-w-0 items-center gap-1.5 border-r border-zinc-200 bg-white px-3 py-0 relative" style={{ borderTop: "1px solid #18181b" }}>
          {/* top accent bar */}
          <svg
            className="h-3.5 w-3.5 flex-shrink-0 text-zinc-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.5}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
          </svg>
          <span className="truncate font-mono text-[11px] text-zinc-600 py-2" style={{ maxWidth: "160px" }}>
            {slug}.md
          </span>
        </div>

        {/* Spacer — rest of the tab strip */}
        <div className="flex flex-1 items-center justify-end gap-2 px-3 py-1.5">
          <CopyButton text={node.content} label="Copy file" />
          <div className="h-3.5 w-px bg-zinc-300" />
          <span className={`flex-shrink-0 rounded border px-1.5 py-0.5 font-mono text-[9px] font-semibold tracking-widest ${TYPE_STYLES[node.type]}`}>
            {node.type.toUpperCase()}
          </span>
        </div>
      </div>

      {/* ── Breadcrumb ───────────────────────────────────────────────────── */}
      <div className="flex flex-shrink-0 items-center gap-1 border-b border-zinc-100 bg-white px-4 py-1.5">
        <span className="font-mono text-[10px] text-zinc-300">skills</span>
        <svg className="h-2.5 w-2.5 flex-shrink-0 text-zinc-200" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
        </svg>
        <span className="font-mono text-[10px] text-zinc-400">{slug}.md</span>
      </div>

      {/* ── Description ──────────────────────────────────────────────────── */}
      <div className="flex-shrink-0 border-b border-zinc-100 bg-white px-4 py-2.5">
        <p className="text-[11px] leading-relaxed text-zinc-400">
          {node.description}
        </p>
        {node.evidence && node.evidence.length > 0 && (
          <div className="mt-2 border-t border-zinc-100 pt-2">
            <p className="mb-1 text-[10px] uppercase tracking-widest text-zinc-400">Evidence</p>
            <ul className="space-y-1">
              {node.evidence.slice(0, 5).map((ev, idx) => (
                <li key={`${ev.path}-${idx}`} className="text-[10px] text-zinc-500">
                  <code className="rounded bg-zinc-100 px-1 py-0.5">{ev.path}</code>
                  {ev.start_line ? `:${ev.start_line}` : ""}
                  {ev.end_line ? `-${ev.end_line}` : ""}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* ── Markdown document body ───────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto px-5 py-5">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            h1: ({ children }) => (
              <h1 className="mb-5 mt-0 text-lg font-bold text-zinc-900" style={{ letterSpacing: "-0.03em" }}>
                {children}
              </h1>
            ),
            h2: ({ children }) => (
              <h2 className="mb-2 mt-7 text-[11px] font-bold uppercase tracking-widest text-zinc-400 border-b border-zinc-100 pb-1.5">
                {children}
              </h2>
            ),
            h3: ({ children }) => (
              <h3 className="mb-2 mt-5 text-xs font-semibold text-zinc-600" style={{ letterSpacing: "-0.01em" }}>
                {children}
              </h3>
            ),
            p: ({ children }) => {
              const processed = React.Children.map(children, (child) => {
                if (typeof child === "string") {
                  return processWikilinks(child);
                }
                return child;
              });
              return (
                <p className="mb-4 text-[13px] leading-[1.8] text-zinc-600">
                  {processed}
                </p>
              );
            },
            code: ({ className, children, ...props }) => {
              const lang = className?.replace("language-", "") ?? "";
              const isBlock = !!className?.startsWith("language-");

              if (isBlock) {
                return (
                  <div className="mb-5 overflow-hidden rounded-md border border-zinc-200 bg-white">
                    <div className="flex items-center justify-between border-b border-zinc-100 bg-zinc-50 px-3.5 py-1.5">
                      <span className="font-mono text-[9px] font-semibold uppercase tracking-widest text-zinc-400">
                        {lang || "code"}
                      </span>
                      <CopyButton text={String(children)} />
                    </div>
                    <div className="overflow-x-auto px-4 py-3.5">
                      <code
                        className={`block font-mono text-[11px] leading-relaxed text-zinc-700 ${className ?? ""}`}
                        {...props}
                      >
                        {children}
                      </code>
                    </div>
                  </div>
                );
              }

              return (
                <code
                  className="rounded bg-zinc-100 px-1.5 py-0.5 font-mono text-[11px] text-zinc-700"
                  {...props}
                >
                  {children}
                </code>
              );
            },
            pre: ({ children }) => <>{children}</>,
            ul: ({ children }) => (
              <ul className="mb-4 space-y-1.5 pl-4 text-[13px] text-zinc-600" style={{ listStyleType: "disc" }}>
                {children}
              </ul>
            ),
            ol: ({ children }) => (
              <ol className="mb-4 space-y-1.5 pl-4 text-[13px] text-zinc-600" style={{ listStyleType: "decimal" }}>
                {children}
              </ol>
            ),
            li: ({ children }) => (
              <li className="leading-[1.8]">{children}</li>
            ),
            blockquote: ({ children }) => (
              <blockquote className="mb-4 border-l-2 border-zinc-200 pl-4 text-[13px] italic text-zinc-400">
                {children}
              </blockquote>
            ),
            a: ({ href, children }) => (
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="text-zinc-900 underline decoration-zinc-300 underline-offset-2 transition-colors hover:decoration-zinc-900"
              >
                {children}
              </a>
            ),
            table: ({ children }) => (
              <div className="mb-5 overflow-x-auto rounded-md border border-zinc-200">
                <table className="w-full border-collapse text-[11px]">
                  {children}
                </table>
              </div>
            ),
            th: ({ children }) => (
              <th className="border-b border-zinc-200 bg-zinc-50 px-4 py-2 text-left text-[10px] font-semibold uppercase tracking-wider text-zinc-500">
                {children}
              </th>
            ),
            td: ({ children }) => (
              <td className="border-b border-zinc-100 px-4 py-2 text-[11px] text-zinc-600">
                {children}
              </td>
            ),
            hr: () => (
              <hr className="my-6 border-zinc-100" />
            ),
          }}
        >
          {node.content}
        </ReactMarkdown>
      </div>
    </div>
  );
}
