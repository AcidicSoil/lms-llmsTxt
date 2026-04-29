# OSS Alternatives to HyperGraph Stack

This project currently uses:
- `react-force-graph-2d` for interactive force-directed graph rendering
- custom markdown graph generation/export pipeline

If we want to replace or extend the current stack with OSS-first alternatives, use the staged path below.

## Candidate Replacements

| Layer | Current | OSS Alternative | Why Consider It | Tradeoffs |
|---|---|---|---|---|
| Graph Renderer | react-force-graph-2d | Cytoscape.js (+ React wrapper) | Mature ecosystem, huge plugin surface, robust layout engines | Different API and styling model; migration effort |
| Graph Renderer | react-force-graph-2d | Sigma.js + Graphology | High performance for large graphs, modern graph tooling | More setup and data-shaping than current stack |
| Graph Renderer | react-force-graph-2d | Vis Network | Easy interaction model, stable physics controls | Visual styling is less custom by default |
| Graph Layout | d3-force via react-force-graph | ELK.js / Dagre / Cola | Deterministic, reproducible layouts for docs/snapshots | Loses organic force simulation feel unless hybridized |
| Graph Persistence | SQLite + Drizzle | Postgres + Drizzle | Multi-user and hosted scale | Operational complexity vs local SQLite simplicity |

## Recommended Path (Low Risk)

1. Keep `react-force-graph-2d` as default renderer.
2. Add a renderer adapter interface (`GraphRendererAdapter`) so renderers are swappable.
3. Implement a second renderer behind feature flag for A/B testing (recommend: Cytoscape.js).
4. Measure parity on:
   - node/edge count support
   - hover/selection latency
   - zoom/pan behavior
   - force/layout visual quality
5. Promote alternative renderer only after parity + perf gates pass.

## Migration Milestones

1. **Adapter extraction**
   - Separate render logic from app state logic.
   - Keep shared props/types in `types/graph.ts`.

2. **Dual-renderer toggle**
   - Add `NEXT_PUBLIC_GRAPH_RENDERER` (`forcegraph2d` | `cytoscape`).
   - Keep fallback to `forcegraph2d` for invalid values.

3. **Parity suite**
   - Smoke test: generate graph, select node, zoom/pan, export files.
   - Verify dark mode rendering consistency.

4. **Cutover option**
   - Make renderer selectable in UI (advanced setting) after validation.

## Decision Criteria

Choose the replacement only if all are true:
- equal or better interaction smoothness on medium graphs (100-500 nodes)
- no regression in selection, hover, or zoom behavior
- type-safe integration (no `any` escapes)
- build/lint/test all green in CI

## Initial Recommendation

If the goal is a true OSS replacement with strong long-term maintainability, start with **Cytoscape.js** as secondary renderer while retaining the existing force renderer as default until parity is proven.
