# Architecture and Code Patterns (Brownfield, Discovered)

This document records recurring architectural and implementation patterns found in `lms-llmsTxt`, including integration patterns across the Python generator, MCP server, and HyperGraph UI.

Scope:
- `src/lms_llmsTxt/**`
- `src/lms_llmsTxt_mcp/**`
- `hypergraph/app/**`, `hypergraph/components/**`, `hypergraph/lib/**`, `hypergraph/types/**`

Tests are excluded from this pass by user choice.

## Confidence Summary

- Overall pattern confidence: **82%**
- Core generation pipeline patterns: **90%**
- MCP resource/tool patterns: **88%**
- HyperGraph UI/API patterns: **80%**
- Cross-runtime operational patterns: **68%** (environment-sensitive, needs human validation)

## Pattern 1: Orchestrator Pipeline (CLI -> Config -> Pipeline)

### What it is
A thin CLI entrypoint that parses user input, maps flags into config, and delegates the full workflow to a single pipeline function.

### Where it appears
- `src/lms_llmsTxt/cli.py`
- `src/lms_llmsTxt/pipeline.py`

### Why it exists
- Keeps CLI concerns (flags, UX, summary printing) separate from orchestration logic.
- Makes pipeline behavior reusable from tests and other entrypoints.

### Tradeoffs
- CLI summary formatting becomes a de facto interface that can break downstream parsing if changed casually.

### Reuse guidance
- New generation features should be added to `run_generation(...)` first, then surfaced via CLI flags.

## Pattern 2: Resilient Primary/Fallback Generation

### What it is
The system attempts primary DSPy/LM Studio generation first, then falls back to heuristic JSON/markdown output when provider/runtime failures occur.

### Where it appears
- `src/lms_llmsTxt/pipeline.py`
- `src/lms_llmsTxt/fallback.py`
- `src/lms_llmsTxt/reasoning.py`

### Why it exists
- Artifact delivery is prioritized over provider dependence.
- Enables local/dev/CI runs to produce usable outputs even during model runtime failures.

### Tradeoffs
- Fallback outputs may be lower fidelity than primary model outputs.
- Documentation and validation must clearly distinguish fallback success from primary-path success.

### Reuse guidance
- New provider integrations should preserve this contract: `llms.txt` artifact generation should not fail hard for recoverable provider/runtime issues.

## Pattern 3: Budget-Aware Retry Reduction Loop

### What it is
Prompt/context budget is estimated before generation, then reduced and retried for specific error classes (context length / payload limits).

### Where it appears
- `src/lms_llmsTxt/context_budget.py`
- `src/lms_llmsTxt/context_compaction.py`
- `src/lms_llmsTxt/retry_policy.py`
- `src/lms_llmsTxt/pipeline.py`

### Why it exists
- Large repositories create prompt-size pressure.
- Retrying with deterministic reductions is more reliable than generic retries.

### Tradeoffs
- Compaction can reduce context richness, potentially affecting output quality.

### Reuse guidance
- Preserve the sequence: classify error -> decide retry budget -> compact -> retry.
- Avoid retrying unknown errors without classification.

## Pattern 4: Provider Output Normalization Adapter

### What it is
Model/provider outputs are normalized before downstream use to avoid brittle assumptions about response shape and sparsity.

### Where it appears
- `src/lms_llmsTxt/analyzer.py`
- `src/lms_llmsTxt/reasoning.py`

### Why it exists
- LLM/provider SDK responses are variable (dicts, objects, partial fields).
- Prevents runtime crashes from missing attributes/fields.

### Tradeoffs
- Normalization can mask upstream provider regressions if logging/metrics are insufficient.

### Reuse guidance
- Add new normalization helpers for new providers instead of sprinkling `getattr(..., None)` logic across the pipeline.

## Pattern 5: Artifact-As-Contract Across Subsystems

### What it is
The filesystem artifact set (`llms.txt`, graph JSON, node markdowns) acts as the integration boundary between Python generation, MCP serving, and UI visualization.

### Where it appears
- `src/lms_llmsTxt/pipeline.py` (artifact emission)
- `src/lms_llmsTxt/graph_builder.py` (graph files)
- `src/lms_llmsTxt_mcp/server.py` / `graph_resources.py` (artifact discovery/read)
- `hypergraph/lib/generator.ts` / `hypergraph/app/page.tsx` (load by path)

### Why it exists
- Decouples runtime environments (Python process, MCP client, Next.js app).
- Enables offline inspection and reproducible runs.

### Tradeoffs
- Path conventions become compatibility-sensitive.
- Cross-platform path handling can become fragile if assumptions drift.

### Reuse guidance
- Treat artifact path and schema changes as versioned interface changes, not internal refactors.

## Pattern 6: MCP Tool + Resource Dual Access

### What it is
Artifacts are exposed both as MCP tools (listing/reading operations) and MCP resources (URI-addressable content).

### Where it appears
- `src/lms_llmsTxt_mcp/server.py`
- `src/lms_llmsTxt_mcp/graph_resources.py`

### Why it exists
- Tools support operational workflows and pagination controls.
- Resources support direct URI-based consumption by agents/clients.

### Tradeoffs
- Duplicated capabilities must remain behaviorally consistent.

### Reuse guidance
- When adding a new artifact family, add both a discoverability path and a direct read path (tool/resource pair) where practical.

## Pattern 7: Path Safety Validation for Resource Access

### What it is
Resource access is constrained through allowed-root scanning and safe path segment validation.

### Where it appears
- `src/lms_llmsTxt_mcp/graph_resources.py`
- `src/lms_llmsTxt_mcp/security.py` (related security concerns)

### Why it exists
- MCP resource readers expose local disk content and need path traversal protections.

### Tradeoffs
- Strict validation can reject legitimate-but-unexpected identifiers if naming conventions change.

### Reuse guidance
- New MCP path-based readers should reuse the same validation pattern (`allowed root` + constrained segment regex).

## Pattern 8: Mode-Based Next.js API Route Multiplexing

### What it is
A single `POST /api/generate` route branches on `mode` to support multiple workflows:
- topic graph generation
- load existing repo graph
- generate repo graph via local Python CLI

### Where it appears
- `hypergraph/app/api/generate/route.ts`

### Why it exists
- Consolidates UI graph operations behind one endpoint.
- Reduces route sprawl for a small app.

### Tradeoffs
- Mode branching can become hard to maintain if request/response contracts diverge significantly.

### Reuse guidance
- Keep each mode isolated with explicit input validation and response shape comments/types.
- Split routes if mode-specific behavior grows substantially.

## Pattern 9: Query-Param Handoff for CLI -> UI Flow

### What it is
CLI prints a URL containing mode and graph path query params; the UI parses those params and auto-loads the artifact once.

### Where it appears
- `src/lms_llmsTxt/cli.py` (`build_graph_viewer_url`)
- `hypergraph/app/page.tsx` (`useSearchParams`, `autoLoad` handling)

### Why it exists
- Enables copy/paste handoff from local CLI runs to the visualizer without tight process coupling.

### Tradeoffs
- Query-param contracts are brittle if renamed without coordinated updates.
- URL-encoded filesystem paths can be confusing to users when debugging manually.

### Reuse guidance
- Treat handoff params as a stable mini-contract (`mode`, `graphPath`, `autoLoad`).

## Pattern 10: UI Workflow Convergence on Shared Viewer State

### What it is
Multiple UI workflows (topic generation, repo generation, load existing graph) converge on the same graph/file/selection state model.

### Where it appears
- `hypergraph/app/page.tsx`
- `hypergraph/types/graph.ts`

### Why it exists
- Reuses rendering and preview components without branching the view layer.

### Tradeoffs
- The page component can accumulate too much orchestration state and grow large.

### Reuse guidance
- If additional workflows are added, extract state transitions into a reducer or local controller hook before complexity expands further.

## Anti-Patterns / Hotspots (Observed)

### 1. Third-party typing friction in graph rendering component

- `hypergraph/components/GraphView.tsx` contains `any` usage and build-time typing mismatches (`d3Force` prop typing issue).
- Impact: `eslint` and `next build` failures block a clean frontend verification pipeline.
- Recommendation: wrap `react-force-graph-2d` in a typed adapter or local component abstraction.
- Confidence: **95%** (directly observed during lint/build runs)

### 2. Working tree noise from generated artifacts

- `artifacts/**` changes can accumulate during normal validation/E2E runs.
- Impact: makes review diffs noisy and can obscure intentional source changes.
- Recommendation: establish a documented workflow for retaining or cleaning generated artifacts before commits.
- Confidence: **85%**

### 3. Cross-runtime operational assumptions are implicit

- HyperGraph repo-generation mode assumes local Python, `PYTHONPATH`, and LM Studio/GitHub env setup.
- Impact: UI repo generation may fail in environments where the CLI works differently (or vice versa).
- Recommendation: document preflight checks in UI docs and optionally add a health/preflight API mode later.
- Confidence: **70%** (inferred from code + runtime coupling)

## Extension Pattern Recommendations

1. Prefer additive interfaces.
- Add new CLI flags, MCP resources, or HyperGraph modes without renaming existing ones unless a migration plan is documented.

2. Keep adapter layers explicit.
- Python: provider output normalization and fallback mapping.
- UI: route mode validation and response typing.

3. Preserve artifact compatibility.
- Treat `repo.graph.json`, node markdown structure, and MCP graph resource URIs as shared contracts.

4. Document coupling points immediately.
- When adding a new cross-runtime handoff (CLI -> UI, UI -> CLI, MCP -> filesystem), record it in `docs/architecture.md` and this file.
