"use client";

import { useRef, useEffect, useState, useCallback } from "react";
import dynamic from "next/dynamic";
import type { ForceGraphData, NodeType } from "@/types/graph";
import type { ForceGraphMethods, LinkObject, NodeObject } from "react-force-graph-2d";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
  ssr: false,
});

interface GraphViewProps {
  data: ForceGraphData;
  onNodeClick: (nodeId: string) => void;
  selectedNodeId: string | null;
}

type GraphNodeObject = NodeObject;
type GraphLinkObject = LinkObject;
type GraphMethods = ForceGraphMethods;

type ChargeForce = {
  strength: (value: number) => ChargeForce;
  distanceMax: (value: number) => ChargeForce;
};

type LinkForce = {
  distance: (fn: (link: GraphLinkObject) => number) => LinkForce;
};

const R = 3.5; // base radius multiplier, reduced to avoid clutter

type NodeVisualStyle = {
  fill: string;
  stroke: string;
  strokeW: number;
  innerDot: boolean;
};

type GraphPalette = {
  nodes: Record<NodeType, NodeVisualStyle>;
  gridDot: string;
  background: string;
  link: string;
  particle: string;
  selectedHalo: string;
  selectedRing: string;
  hoverRing: string;
  shadow: string;
  selectedFill: string;
  selectedStroke: string;
  innerDot: string;
  labelHalo: string;
  label: string;
  selectedLabel: string;
};

const GRAPH_PALETTES: Record<"light" | "dark", GraphPalette> = {
  light: {
    nodes: {
      moc: { fill: "#18181b", stroke: "#000000", strokeW: 0, innerDot: true },
      concept: { fill: "#27272a", stroke: "#000000", strokeW: 0, innerDot: false },
      pattern: { fill: "#52525b", stroke: "#000000", strokeW: 0, innerDot: false },
      gotcha: { fill: "#ffffff", stroke: "#d4d4d8", strokeW: 1.5, innerDot: false },
    },
    gridDot: "#d4d4d8",
    background: "#fafafa",
    link: "rgba(161,161,170,0.4)",
    particle: "rgba(0,0,0,0.6)",
    selectedHalo: "rgba(0,0,0,0.04)",
    selectedRing: "rgba(0,0,0,0.8)",
    hoverRing: "rgba(0,0,0,0.15)",
    shadow: "rgba(0,0,0,0.12)",
    selectedFill: "#ffffff",
    selectedStroke: "#000000",
    innerDot: "rgba(255,255,255,0.85)",
    labelHalo: "rgba(255,255,255,0.95)",
    label: "#404040",
    selectedLabel: "#000000",
  },
  dark: {
    nodes: {
      moc: { fill: "#f4f4f5", stroke: "#ffffff", strokeW: 0, innerDot: true },
      concept: { fill: "#d4d4d8", stroke: "#ffffff", strokeW: 0, innerDot: false },
      pattern: { fill: "#a1a1aa", stroke: "#ffffff", strokeW: 0, innerDot: false },
      gotcha: { fill: "#18181b", stroke: "#71717a", strokeW: 1.5, innerDot: false },
    },
    gridDot: "#27272a",
    background: "#09090b",
    link: "rgba(113,113,122,0.5)",
    particle: "rgba(244,244,245,0.75)",
    selectedHalo: "rgba(244,244,245,0.10)",
    selectedRing: "rgba(244,244,245,0.9)",
    hoverRing: "rgba(244,244,245,0.24)",
    shadow: "rgba(0,0,0,0.45)",
    selectedFill: "#09090b",
    selectedStroke: "#f4f4f5",
    innerDot: "rgba(9,9,11,0.85)",
    labelHalo: "rgba(9,9,11,0.96)",
    label: "#d4d4d8",
    selectedLabel: "#ffffff",
  },
};

const LEGEND: { type: NodeType; label: string }[] = [
  { type: "moc", label: "MOC" },
  { type: "concept", label: "Concept" },
  { type: "pattern", label: "Pattern" },
  { type: "gotcha", label: "Gotcha" },
];

export default function GraphView({
  data,
  onNodeClick,
  selectedNodeId,
}: GraphViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<GraphMethods | undefined>(undefined);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const palette = GRAPH_PALETTES[theme];

  useEffect(() => {
    const updateTheme = () => {
      setTheme(
        document.documentElement.getAttribute("data-theme") === "dark"
          ? "dark"
          : "light",
      );
    };

    updateTheme();
    const observer = new MutationObserver(updateTheme);
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-theme"],
    });

    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const observer = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect;
      setDimensions({ width, height });
    });
    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!graphRef.current) {
      return;
    }

    const chargeForce = graphRef.current.d3Force("charge") as ChargeForce | undefined;
    chargeForce?.strength(-350);
    chargeForce?.distanceMax(500);

    const linkForce = graphRef.current.d3Force("link") as LinkForce | undefined;
    linkForce?.distance((link: GraphLinkObject) => {
      const sourceType =
        typeof link.source === "object" && link.source !== null && "type" in link.source
          ? link.source.type
          : undefined;
      const targetType =
        typeof link.target === "object" && link.target !== null && "type" in link.target
          ? link.target.type
          : undefined;
      return sourceType === "moc" || targetType === "moc" ? 180 : 90;
    });

    graphRef.current.d3ReheatSimulation();

    if (data.nodes.length > 0) {
      setTimeout(() => graphRef.current?.zoomToFit(400, 60), 500);
    }
  }, [data]);

  const nodeCanvasObject = useCallback(
    (node: GraphNodeObject, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const type = typeof node.type === "string" ? (node.type as NodeType) : "concept";
      const style = palette.nodes[type] ?? palette.nodes.concept;
      const size = (typeof node.val === "number" ? node.val : 1) * R;
      const x = node.x ?? 0;
      const y = node.y ?? 0;
      const isSelected = node.id === selectedNodeId;
      const isHovered = node.id === hoveredNode && !isSelected;

      // ── Selection rings ──────────────────────────────────────────────────
      if (isSelected) {
        // Outer diffuse halo
        ctx.beginPath();
        ctx.arc(x, y, size + 8, 0, 2 * Math.PI);
        ctx.strokeStyle = palette.selectedHalo;
        ctx.lineWidth = 6;
        ctx.stroke();
        // Crisp selection ring
        ctx.beginPath();
        ctx.arc(x, y, size + 4, 0, 2 * Math.PI);
        ctx.strokeStyle = palette.selectedRing;
        ctx.lineWidth = 1.5;
        ctx.stroke();
      } else if (isHovered) {
        ctx.beginPath();
        ctx.arc(x, y, size + 4, 0, 2 * Math.PI);
        ctx.strokeStyle = palette.hoverRing;
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }

      // ── Node body ─────────────────────────────────────────────────────────
      ctx.beginPath();
      ctx.arc(x, y, size, 0, 2 * Math.PI);

      // Shadow for depth
      ctx.shadowColor = palette.shadow;
      ctx.shadowBlur = 6;
      ctx.shadowOffsetX = 0;
      ctx.shadowOffsetY = 2;

      if (isSelected) {
        ctx.fillStyle = palette.selectedFill;
        ctx.fill();
        ctx.shadowColor = "transparent"; // clear shadow for stroke
        ctx.strokeStyle = palette.selectedStroke;
        ctx.lineWidth = 2;
        ctx.stroke();
      } else {
        ctx.fillStyle = style.fill;
        ctx.fill();
        ctx.shadowColor = "transparent"; // clear shadow for stroke
        if (style.stroke !== "none") {
          ctx.strokeStyle = style.stroke;
          ctx.lineWidth = style.strokeW;
          ctx.stroke();
        }
      }

      // ── Inner accent dot (moc nodes) ─────────────────────────────────────
      if (style.innerDot && !isSelected) {
        ctx.beginPath();
        ctx.arc(x, y, size * 0.35, 0, 2 * Math.PI);
        ctx.fillStyle = palette.innerDot;
        ctx.fill();
      }

      // ── Label — with high-contrast halo ──────────────────────────────────
      const fontSize = Math.max(10 / globalScale, 2.2);
      const weight = isSelected ? "700" : "500";
      (
        ctx as CanvasRenderingContext2D & { letterSpacing?: string }
      ).letterSpacing = "-0.02em";
      ctx.font = `${weight} ${fontSize}px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`;

      const label = node.label ?? "";
      const ly = y + size + 7;

      ctx.textAlign = "center";
      ctx.textBaseline = "top";

      // 1. Thick white halo (stroke) to create separation from background/other nodes
      ctx.lineJoin = "round";
      ctx.lineWidth = 3.5;
      ctx.strokeStyle = palette.labelHalo;
      ctx.strokeText(label, x, ly);

      // 2. The text itself
      ctx.fillStyle = isSelected ? palette.selectedLabel : palette.label;
      ctx.fillText(label, x, ly);

      // Reset
      (
        ctx as CanvasRenderingContext2D & { letterSpacing?: string }
      ).letterSpacing = "0px";
    },
    [selectedNodeId, hoveredNode, palette],
  );

  const nodePointerAreaPaint = useCallback(
    (node: GraphNodeObject, color: string, ctx: CanvasRenderingContext2D) => {
      const size = (typeof node.val === "number" ? node.val : 1) * R;
      ctx.beginPath();
      ctx.arc(node.x ?? 0, node.y ?? 0, size + 8, 0, 2 * Math.PI);
      ctx.fillStyle = color;
      ctx.fill();
    },
    [],
  );

  return (
    <div
      ref={containerRef}
      className="relative h-full w-full"
      style={{
        backgroundImage:
          `radial-gradient(circle, ${palette.gridDot} 1px, transparent 1px)`,
        backgroundSize: "28px 28px",
        backgroundColor: palette.background,
      }}
    >
      <ForceGraph2D
        ref={graphRef}
        width={dimensions.width}
        height={dimensions.height}
        graphData={data}
        nodeCanvasObject={nodeCanvasObject}
        nodePointerAreaPaint={nodePointerAreaPaint}
        onNodeClick={(node) => {
          if (node.id != null) {
            onNodeClick(String(node.id));
          }
        }}
        onNodeHover={(node) => setHoveredNode(node?.id != null ? String(node.id) : null)}
        linkColor={() => palette.link}
        linkWidth={1.2}
        linkDirectionalParticles={2}
        linkDirectionalParticleWidth={2}
        linkDirectionalParticleColor={() => palette.particle}
        backgroundColor="transparent"
        d3AlphaDecay={0.04}
        d3VelocityDecay={0.2}
        cooldownTicks={100}
        onEngineStop={() => graphRef.current?.zoomToFit(400, 60)}
      />

      {/* Legend */}
      <div className="pointer-events-none absolute bottom-4 left-4 rounded-lg border border-zinc-200 bg-white/90 px-3 py-2.5 shadow-sm backdrop-blur-sm">
        <p className="accent mb-2 text-[9px] font-semibold text-zinc-400">
          Node types
        </p>
        <div className="flex flex-col gap-1.5">
          {LEGEND.map(({ type, label }) => (
            <div key={type} className="flex items-center gap-2">
              <div
                className="h-2.5 w-2.5 flex-shrink-0 rounded-full"
                style={{
                  backgroundColor: palette.nodes[type].fill,
                  border:
                    palette.nodes[type].stroke !== "none"
                      ? `1.5px solid ${palette.nodes[type].stroke}`
                      : "none",
                  outline:
                    type === "moc"
                      ? `2px solid ${theme === "dark" ? "rgba(244,244,245,0.18)" : "rgba(0,0,0,0.12)"}`
                      : "none",
                  outlineOffset: "1px",
                }}
              />
              <span className="accent text-[9px] font-semibold text-zinc-500">
                {label}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
