# Architecture Overview

This document explains how `lms-llmsTxt` is organized and how data moves from a repository URL to generated artifacts and visualizations.

This is a brownfield documentation pass in **supplement mode**. It preserves prior architectural framing while adding explicit contracts for the HyperGraph visualizer integration and newer MCP graph resources.

## Confidence Summary

- Overall architecture confidence: **87%**
- Python generator pipeline: **93%**
- MCP server and resource contracts: **90%**
- HyperGraph UI and route flow: **85%**
- Cross-runtime operational assumptions: **72%** (environment-dependent)

## System Design

`lms-llmsTxt` is a multi-interface local toolkit with three primary surfaces:

1. Python CLI (`lmstxt`) for repository generation
2. Python MCP server (`lmstxt-mcp`) for agent tool/resource access
3. Next.js HyperGraph UI (`hypergraph/`) for graph generation/loading/inspection

These surfaces share a filesystem artifact contract under `artifacts/<owner>/<repo>/`.

## High-Level Flow

```text
User (CLI / MCP / HyperGraph UI)
  -> Input validation/config
  -> Repository material collection (GitHub API)
  -> Budget preflight and compaction
  -> Analyzer generation (DSPy + LM Studio)
      -> primary path (normal)
      -> fallback path (resilient output)
  -> Optional graph build
  -> Artifact write to artifacts/<owner>/<repo>/
  -> Consumption via:
      - CLI summary output
      - MCP tools/resources
      - HyperGraph UI loader / viewer
```

## Core Components

1. `src/lms_llmsTxt/cli.py`
- CLI interface and runtime options.
- Maps command-line flags into `AppConfig` and `run_generation(...)`.
- Builds HyperGraph handoff URLs via `build_graph_viewer_url(...)`.

2. `src/lms_llmsTxt/pipeline.py`
- Main orchestration pipeline.
- Handles budget checks, retries, fallback behavior, sanitization, artifact writing, and optional graph generation.

3. `src/lms_llmsTxt/analyzer.py`
- DSPy-based semantic extraction and markdown synthesis.
- Uses normalization/default synthesis to survive sparse provider outputs.

4. `src/lms_llmsTxt/repo_digest.py`
- Digest construction for repository material (used by generation and graph building workflows).

5. `src/lms_llmsTxt/graph_builder.py`
- Builds grounded graph artifacts:
  - `repo.graph.json`
  - `repo.force.json`
  - `graph/nodes/*.md`

6. `src/lms_llmsTxt_mcp/server.py`
- FastMCP server entrypoint.
- Exposes generation tools and artifact resources for external agent clients.

7. `src/lms_llmsTxt_mcp/graph_resources.py`
- Graph resource discovery and URI mapping.
- Supports both `lmstxt://graphs/...` and `repo://{repo_id}/graph/nodes/{node_id}` access patterns.
- Performs safe node-id validation for path access.

8. `hypergraph/app/page.tsx`
- Primary visualizer UI.
- Supports topic graph generation, repo graph generation (via local CLI invocation through route handler), and loading existing graph artifacts.
- Supports query-param handoff (`mode`, `graphPath`, `autoLoad`) from the Python CLI.

9. `hypergraph/app/api/generate/route.ts`
- Next.js API route multiplexing graph-related operations.
- Handles:
  - topic generation
  - `load-repo-graph`
  - `generate-repo-graph`

10. `hypergraph/lib/generator.ts`
- Topic graph generation using OpenAI.
- Local repo graph loading and local Python CLI invocation for repo generation (`generateRepoGraph(...)`).

## Directory Structure

```text
src/
  lms_llmsTxt/
    cli.py
    config.py
    pipeline.py
    analyzer.py
    repo_digest.py
    graph_builder.py
    graph_models.py
    context_budget.py
    context_compaction.py
    retry_policy.py
    reasoning.py
    fallback.py
    github.py
    lmstudio.py
    models.py
  lms_llmsTxt_mcp/
    server.py
    generator.py
    runs.py
    artifacts.py
    graph_resources.py
    session_memory.py
    security.py
hypergraph/
  app/
    page.tsx
    api/generate/route.ts
  components/
    GraphView.tsx
    NodePreview.tsx
    FileTreePanel.tsx
    TopicInput.tsx
  lib/
    generator.ts
    hyperbrowser.ts
    serper.ts
  types/
    graph.ts
tests/
docs/
artifacts/
```

## Interface Contracts (Public and Compatibility-Sensitive)

## CLI Interface (`lmstxt`)

Key flags and behavior are implemented in `src/lms_llmsTxt/cli.py`.

Notable interface groups:
- Generation/runtime: `--model`, `--api-base`, `--api-key`, `--output-dir`
- Artifact controls: `--stamp`, `--no-ctx`, `--generate-graph`, `--graph-only`
- Budget controls: `--max-context-tokens`, `--max-output-tokens`, `--context-headroom`, `--verbose-budget`
- Session memory: `--enable-session-memory`
- UI handoff: `--ui`, `--ui-base-url`

Compatibility note:
- `--ui` requires graph generation so `repo.graph.json` exists (enforced by CLI validation).

## Artifact File Contract

Artifacts are written under:
- `artifacts/<owner>/<repo>/`

Common outputs:
- `<repo>-llms.txt`
- `<repo>-llms-full.txt` (unless graph-only mode)
- `<repo>-llms.json` (fallback payload, when fallback path is used)
- `graph/repo.graph.json`
- `graph/repo.force.json`
- `graph/nodes/*.md`

These files are consumed by both the MCP server and HyperGraph UI.

## MCP Tool and Resource Contracts

MCP tools/resources are exposed in `src/lms_llmsTxt_mcp/server.py` and backed by helpers such as `src/lms_llmsTxt_mcp/graph_resources.py`.

Documented contracts (additive, compatibility-sensitive):
- Graph file resources: `lmstxt://graphs/{filename}`
- Repo node resources: `repo://{repo_id}/graph/nodes/{node_id}`
- Graph listing/reading tools for artifact discovery and chunked reads

Security posture (observed):
- Local file reads are constrained to an allowed root and validated path segments.

## HyperGraph API Route Contract (`POST /api/generate`)

Implemented in `hypergraph/app/api/generate/route.ts`.

Supported modes:
1. Topic generation (default path when `mode` absent and `topic` is present)
2. `load-repo-graph`
- Input: `graphPath`
- Output: `{ graph, files }`
3. `generate-repo-graph`
- Input: `repoUrl`
- Output: `{ graph, files, artifactPath }`

Error contract (observed):
- JSON responses using `{ error: string }` with HTTP status codes

## HyperGraph CLI -> UI Handoff Contract

The CLI builds a URL with query params that the UI parses on load.

Query params used:
- `mode=load-repo-graph`
- `graphPath=<url-encoded-path>`
- `autoLoad=1`

Observed implementation:
- URL builder: `src/lms_llmsTxt/cli.py`
- Query parsing and one-time autoload guard: `hypergraph/app/page.tsx`

## Data Flow Details

## 1) CLI or MCP entry
- CLI parses args and builds `AppConfig` in `src/lms_llmsTxt/cli.py`.
- MCP invokes generation and read flows through server handlers in `src/lms_llmsTxt_mcp/server.py`.

## 2) Repository collection
- `src/lms_llmsTxt/github.py` gathers repository material (README, file tree, metadata, package/config files).

## 3) Budgeting and compaction
- `src/lms_llmsTxt/context_budget.py` estimates context usage.
- `src/lms_llmsTxt/context_compaction.py` compacts inputs when needed.
- `src/lms_llmsTxt/retry_policy.py` classifies errors and computes reduced budgets for retries.

## 4) Generation
- `src/lms_llmsTxt/analyzer.py` attempts primary DSPy generation.
- `src/lms_llmsTxt/pipeline.py` catches provider/runtime failures and routes to fallback logic in `src/lms_llmsTxt/fallback.py`.

## 5) Post-processing and artifact persistence
- `src/lms_llmsTxt/reasoning.py` sanitizes outputs.
- `src/lms_llmsTxt/full_builder.py` optionally expands to `llms-full.txt`.
- `src/lms_llmsTxt/graph_builder.py` emits graph artifacts.
- `src/lms_llmsTxt/pipeline.py` writes files into the artifact directory.

## 6) Consumption via MCP
- MCP exposes reads/lists for text and graph artifacts.
- Graph node resources can be read through repo-scoped URIs.

## 7) Consumption via HyperGraph UI
- The UI can:
  - generate topic graphs directly (Hyperbrowser + OpenAI flow)
  - load an existing repo graph by path
  - trigger local repo graph generation using the Python CLI and then load the result
- The viewer and preview panels consume a shared graph response shape (`hypergraph/types/graph.ts`).

## HyperGraph Integration Architecture (Supplemental)

This section supplements the original architecture doc with the newer two-way visualizer wiring.

## A. CLI -> HyperGraph
1. User runs `lmstxt ... --generate-graph --ui`.
2. CLI generates repo graph artifacts.
3. CLI ensures HyperGraph is reachable (reuses a running UI or starts a background dev server), then builds a URL containing `graphPath` and `autoLoad=1`.
4. CLI opens the URL in the default browser (unless disabled via CLI flag); the printed URL remains available for manual use.
5. HyperGraph UI auto-loads `repo.graph.json` and renders the graph.

## B. HyperGraph -> Local Python Generator
1. User enters a GitHub repo URL in the HyperGraph “Generate repo graph” flow.
2. `hypergraph/app/api/generate/route.ts` receives `mode: "generate-repo-graph"`.
3. `hypergraph/lib/generator.ts` invokes local Python (`python3`/`python`) with `-m lms_llmsTxt.cli` and graph flags.
4. Python writes artifacts to the shared `artifacts/` tree.
5. HyperGraph route loads the resulting `repo.graph.json` and returns `{ graph, files, artifactPath }`.
6. UI renders the result and surfaces the artifact path hint.

## Key Design Decisions (Updated)

## 1) Resilience over strict dependence on one provider path

- Primary generation is model-driven.
- Fallback generation ensures artifact delivery even when model calls fail.
- Result: users get outputs reliably in CI/dev environments.

## 2) Deterministic pre-processing

- Budgeting and compaction are deterministic and testable.
- Result: reproducible behavior for large repositories and fewer prompt-size failures.

## 3) MCP-first interoperability

- MCP server exposes artifacts as tools/resources, not only CLI output.
- Result: agent clients can consume repository knowledge without custom glue code.

## 4) Evidence-backed graph outputs

- Graph nodes include provenance/evidence links.
- Result: generated graph content can be traced back to source material.

## 5) Filesystem artifact contract as integration seam (supplemental)

- CLI, MCP, and HyperGraph interoperate through a shared artifact path/schema convention.
- Result: loose coupling across runtimes and easier offline inspection.

## Extension Points

1. Add new fallback strategies in `src/lms_llmsTxt/fallback.py`.
2. Add provider/runtime controls in `src/lms_llmsTxt/lmstudio.py` and `src/lms_llmsTxt/config.py`.
3. Add new MCP tools/resources in `src/lms_llmsTxt_mcp/server.py` and path helpers in `src/lms_llmsTxt_mcp/graph_resources.py`.
4. Add richer graph node semantics in `src/lms_llmsTxt/graph_builder.py` and `src/lms_llmsTxt/graph_models.py`.
5. Split HyperGraph API modes into separate routes if `POST /api/generate` becomes too large or contracts diverge.
6. Add a UI preflight/health check route for Python/LM Studio/GitHub env assumptions.

## Known Constraints and Review Notes

1. Tests were intentionally excluded from this documentation pass.
- Test strategy references here are high-level only.

2. Frontend lint/typecheck cleanliness is currently constrained by `hypergraph/components/GraphView.tsx` third-party typing issues.
- This affects verification confidence for HyperGraph standards, not the architecture shape itself.

3. Cross-runtime operational assumptions (Python executable, `PYTHONPATH`, LM Studio availability) should be validated in target developer environments.
- See `docs/REVIEW_CHECKLIST.md` for manual verification items.

## Testing Strategy (High-Level, Tests Excluded from Deep Analysis)

- Unit coverage exists for core normalization, budgeting, retry policy, graph resources, and CLI behavior.
- MCP integration tests cover stdio tool execution paths.
- E2E CLI validation against public repositories verifies artifact correctness and sanitization.
- HyperGraph UI verification currently depends on manual run + Next.js lint/build checks, with known frontend typing debt noted above.
