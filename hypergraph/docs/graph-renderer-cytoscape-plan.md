# OSS Graph Renderer Extension Plan (Cytoscape Dual-Mode, Exact Force Parity Preserved)

## Summary
Introduce an OSS alternative graph renderer using **Cytoscape.js** while preserving the existing `react-force-graph-2d` behavior as default. Roll out via a typed adapter and dual-renderer toggle, with explicit parity gates for current force tuning/zoom dynamics before any cutover.

This plan is implementation-ready and leaves no open decisions.

## Locked Decisions
- Primary OSS target: **Cytoscape.js** (with `react-cytoscapejs` wrapper).
- Rollout model: **dual mode flag**, no hard replacement.
- Force/layout requirement: **exact current dynamics preserved** on default path; Cytoscape path can be experimental until parity criteria are met.

## Scope
### In Scope
- Adapter abstraction for graph renderer selection.
- New Cytoscape renderer implementation.
- Config + optional UI control for renderer selection.
- Preserve current force graph behavior (typed wrapper, force tuning, zoom-to-fit flow).
- Add parity smoke tests and CI checks.

### Out of Scope
- Removing `react-force-graph-2d`.
- Changing graph generation backend/data model.
- Reworking persistence/search/model-provider flows.

## Architecture Changes
### 1) Add Typed Renderer Contract
Create a renderer interface used by `GraphView`:
- `GraphRendererKind = "forcegraph2d" | "cytoscape"`
- `GraphRendererProps`:
  - `data: ForceGraphData`
  - `selectedNodeId: string | null`
  - `onNodeClick(nodeId: string): void`
  - `onNodeHover?(nodeId: string | null): void`
  - `isDark: boolean`
  - `width: number`
  - `height: number`
- `GraphRendererHandle`:
  - `zoomToFit(durationMs?: number, padding?: number): void`
  - `applyForces?(tuning: GraphForceTuning): void` (optional for non-force renderer)

Files:
- `components/graph/renderers/types.ts`
- `components/graph/renderers/index.ts` (factory/selector)

### 2) Preserve Existing Force Renderer as Default
Refactor current force implementation into:
- `components/graph/renderers/ForceGraphRenderer.tsx`
This wraps existing `TypedForceGraph2D` and preserves:
- current charge/link tuning values
- `zoomToFit` timings
- hover/selection rendering behavior
- current particle/edge/node canvas styling

No behavior changes from today on this path.

### 3) Add Cytoscape Renderer
Implement:
- `components/graph/renderers/CytoscapeRenderer.tsx`
Using:
- `cytoscape`
- `react-cytoscapejs`

Behavior mapping:
- Convert `ForceGraphData` to Cytoscape elements:
  - nodes: `{ data: { id, label, type, val } }`
  - edges: `{ data: { id, source, target } }`
- Dark/light styles mapped from current node type palette.
- Node click: `cy.on("tap", "node", ...) -> onNodeClick(id)`
- Hover: `mouseover/mouseout` events mapped to state callbacks.
- Fit behavior: `cy.fit(undefined, padding)` and animated fit for mount/update.
- Layout:
  - Initial: `cose` with tuned params to approximate current organic layout.
  - Keep layout config centralized for later tuning.

### 4) Renderer Selection
Add selection mechanism (priority order):
1. UI override (session/local persisted)
2. `NEXT_PUBLIC_GRAPH_RENDERER`
3. fallback default: `"forcegraph2d"`

Files:
- `lib/config/graph-renderer.ts` (parse/validate env value)
- `app/page.tsx` (state + optional advanced selector UI)
- `components/GraphView.tsx` (uses renderer factory)

Validation:
- invalid env/string must safely fall back to `forcegraph2d`.

## Public API / Interface Additions
### Environment
- `NEXT_PUBLIC_GRAPH_RENDERER=forcegraph2d|cytoscape`

### Types
Update `types/graph.ts` (or new renderer type module exported from there):
- `export type GraphRendererKind = "forcegraph2d" | "cytoscape";`
- `export interface GraphForceTuning { chargeStrength: number; chargeDistanceMax: number; mocDistance: number; defaultDistance: number; }` (if not already shared from wrapper, centralize to avoid duplicate type sources)

### UI
- Optional “Renderer” selector in advanced controls:
  - labels: `ForceGraph (default)` / `Cytoscape (experimental)`
  - persisted in `localStorage` key: `hypergraph-renderer`

## Implementation Steps
1. Extract shared renderer types + factory.
2. Move current force rendering into `ForceGraphRenderer` with zero functional changes.
3. Implement `CytoscapeRenderer` and element/style/event mapping.
4. Wire `GraphView` to renderer factory and shared handle.
5. Add config parser and optional renderer selector UI.
6. Update docs:
   - `README.md` env var and renderer section
   - `docs/oss-alternatives-hypergraph.md` status updated to “implemented dual mode”
7. Add/adjust tests and smoke scripts.
8. Run lint/build and smoke scenarios; ensure CI remains green.

## Test Cases and Scenarios
### Unit/Type Tests
- Renderer config parser:
  - valid values resolve correctly.
  - invalid/empty values fallback to `forcegraph2d`.
- Data conversion:
  - `ForceGraphData -> Cytoscape elements` preserves node/edge ids and counts.

### Component/Behavior Tests
- `GraphView` renders with both renderer kinds.
- Node click triggers `onNodeClick` with expected id in both renderers.
- Selected node highlighting updates when `selectedNodeId` changes.
- Theme switch updates graph style in both renderers.

### Smoke Tests (manual/CI script)
1. Generate graph from topic.
2. Confirm graph visible with default renderer.
3. Select node from graph and verify preview sync.
4. Toggle dark mode and verify contrast.
5. Switch to Cytoscape renderer and repeat steps 2-4.
6. Resize viewport and confirm graph remains usable.
7. Verify no runtime console errors and build succeeds.

## Acceptance Criteria
- Default user path remains behaviorally identical to current force graph experience.
- App supports two renderer modes with safe fallback.
- No TypeScript `any` regressions introduced in renderer interfaces.
- `npm run lint` and `npm run build` pass.
- Cytoscape renderer is functional and selectable, marked experimental.
- No regressions in node selection, hover, zoom-to-fit, or dark mode behavior.

## Rollout and Monitoring
- Phase 1: ship dual mode with default `forcegraph2d`.
- Phase 2: gather internal feedback on Cytoscape quality/performance.
- Phase 3: only consider default switch after parity sign-off.

Add log field on generation/session UI events (frontend telemetry/logging hook if present):
- `graph.renderer.selected`
- `graph.renderer.render_error` (with renderer kind + message, sanitized)

## Assumptions and Defaults
- Existing `react-force-graph-2d` remains installed and default.
- Cytoscape mode is explicitly labeled experimental at first release.
- Force tuning constants remain exactly:
  - `chargeStrength: -350`
  - `chargeDistanceMax: 500`
  - `mocDistance: 180`
  - `defaultDistance: 90`
- If user/env selection conflicts or is invalid, default is always `forcegraph2d`.
