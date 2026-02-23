# Engineering Standards (Brownfield, Discovered)

This document captures coding and operational conventions observed in the `lms-llmsTxt` repository.

Scope for this pass:
- Python generator and MCP server (`src/lms_llmsTxt`, `src/lms_llmsTxt_mcp`)
- HyperGraph UI (`hypergraph/app`, `hypergraph/components`, `hypergraph/lib`, `hypergraph/types`)
- Project manifests (`pyproject.toml`, `package.json`, `hypergraph/package.json`)

Out of scope for this pass:
- `tests/` deep analysis (explicitly excluded)
- `artifacts/`, `node_modules/`, `.next/`, `.ck/`, virtualenvs, caches

## Confidence Summary

- Overall confidence: **84% (Medium-High)**
- Python packaging/runtime standards: **95%** (explicit in `pyproject.toml`)
- CLI/MCP interface conventions: **90%** (explicit in entrypoints and handlers)
- HyperGraph UI coding conventions: **78%** (explicit in code, but some style/type debt remains)
- Cross-system operational conventions: **72%** (partly inferred from docs + code paths)

## How To Read This Document

- `Discovered` means the behavior is present in current code.
- `Recommended` means a consistency improvement based on current patterns.
- File references point to the current implementations that support the claim.

## 1. Packaging and Runtime Standards

### Discovered

1. Python packaging uses `pyproject.toml` with `setuptools` + `setuptools_scm`.
- Evidence: `pyproject.toml`

2. Python sources are in a `src/` layout.
- Evidence: `pyproject.toml` (`[tool.setuptools.packages.find] where = ["src"]`)

3. CLI entrypoints are package scripts, not shell wrappers.
- `lmstxt = "lms_llmsTxt.cli:main"`
- `lmstxt-mcp = "lms_llmsTxt_mcp.server:main"`
- Evidence: `pyproject.toml`

4. Next.js visualizer is maintained as a separate app under `hypergraph/` with its own `package.json` and scripts.
- Evidence: `hypergraph/package.json`

5. Root `package.json` is used for workflow scripts and wrappers (not as the HyperGraph app package).
- Evidence: `package.json`

### Recommended

1. Keep Python runtime and Node app dependencies isolated (continue separate manifests).
2. Prefer root wrapper scripts for common UI tasks (`ui:dev`, `ui:build`, `ui:start`) to reduce onboarding friction.
3. Avoid checking in incidental lockfile rewrites unless dependency changes are intentional.

## 2. Python Code Standards (Observed)

### Discovered

1. Type hints are used broadly in public functions and dataclasses.
- Examples: `src/lms_llmsTxt/pipeline.py`, `src/lms_llmsTxt/models.py`, `src/lms_llmsTxt_mcp/session_memory.py`

2. `from __future__ import annotations` is consistently used across Python modules.
- Examples: `src/lms_llmsTxt/pipeline.py`, `src/lms_llmsTxt/retry_policy.py`, `src/lms_llmsTxt_mcp/graph_resources.py`

3. Dataclasses are preferred for small structured payloads and return types.
- Examples: `src/lms_llmsTxt/models.py`, `src/lms_llmsTxt/reasoning.py`

4. Logging is centralized through `logging.getLogger(__name__)` and used for pipeline/runtime events.
- Example: `src/lms_llmsTxt/pipeline.py`

5. Helper functions are small and purpose-specific, often used to normalize external/provider output.
- Examples: `src/lms_llmsTxt/analyzer.py`, `src/lms_llmsTxt/reasoning.py`

6. Path handling favors `pathlib.Path` over raw string concatenation in Python code.
- Examples: `src/lms_llmsTxt/cli.py`, `src/lms_llmsTxt/pipeline.py`, `src/lms_llmsTxt_mcp/graph_resources.py`

### Recommended

1. Preserve typed boundaries for public module interfaces (especially CLI, pipeline, MCP resources).
2. Continue using normalization helpers instead of direct attribute access for model/provider outputs.
3. Add inline comments only around non-obvious error classification or compatibility branches.

## 3. CLI and MCP Interface Standards

### Discovered

1. CLI uses `argparse` with explicit named flags and descriptive help text.
- Evidence: `src/lms_llmsTxt/cli.py`

2. CLI maps flags into config first, then calls a single orchestration function (`run_generation`).
- Evidence: `src/lms_llmsTxt/cli.py`, `src/lms_llmsTxt/pipeline.py`

3. CLI prints a human-readable artifact summary after successful runs.
- Evidence: `src/lms_llmsTxt/cli.py`

4. CLI/UI handoff is string-based and filesystem-backed (URL contains `graphPath`, viewer loads local file).
- Evidence: `src/lms_llmsTxt/cli.py` (`build_graph_viewer_url`), `hypergraph/app/page.tsx`, `hypergraph/lib/generator.ts`

5. MCP graph access is exposed via both generic file resources and repo/node-specific resources.
- Evidence: `src/lms_llmsTxt_mcp/server.py`, `src/lms_llmsTxt_mcp/graph_resources.py`

6. MCP graph path resolution validates path segments and rejects unsafe node IDs.
- Evidence: `src/lms_llmsTxt_mcp/graph_resources.py`

### Recommended

1. Treat artifact file formats and MCP URIs as compatibility-sensitive interfaces.
2. Add tests when changing CLI summary output or URL formatting (to avoid downstream workflow regressions).
3. Keep explicit error messages for misused flags (for example `--ui` without `--generate-graph`).

## 4. HyperGraph UI / Next.js Standards (Observed)

### Discovered

1. App Router API route uses mode-based branching in a single `POST` handler.
- Evidence: `hypergraph/app/api/generate/route.ts`

2. API responses use a consistent JSON shape with `NextResponse.json(...)` and simple `{ error: string }` failures.
- Evidence: `hypergraph/app/api/generate/route.ts`

3. Client state is colocated in `hypergraph/app/page.tsx` using React hooks (`useState`, `useEffect`, `useCallback`, `useRef`).
- Evidence: `hypergraph/app/page.tsx`

4. Shared UI payload types are centralized in `hypergraph/types/graph.ts`.
- Evidence: `hypergraph/types/graph.ts`

5. The UI supports multiple workflows (topic generation, repo generation, artifact loading) that converge on a shared viewer state.
- Evidence: `hypergraph/app/page.tsx`

### Discovered Deviations / Debt

1. ESLint currently fails on `@typescript-eslint/no-explicit-any` in `hypergraph/components/GraphView.tsx`.
- Evidence: `hypergraph/components/GraphView.tsx`

2. Next.js production build typecheck currently fails on the `react-force-graph-2d` `d3Force` prop typings in `hypergraph/components/GraphView.tsx`.
- Evidence: `hypergraph/components/GraphView.tsx`

### Recommended

1. Introduce local adapter types or wrapper components for third-party graph library APIs to isolate `any` usage.
2. Keep route mode additions additive and explicit (`mode` enum-like string handling) to avoid breaking current clients.
3. Preserve `hypergraph/types/graph.ts` as the single shared contract for UI and route responses.

## 5. Error Handling and Resilience Standards

### Discovered

1. Generation pipeline prioritizes artifact delivery through a fallback path when primary DSPy/LM Studio generation fails.
- Evidence: `src/lms_llmsTxt/pipeline.py`, `src/lms_llmsTxt/fallback.py`

2. Errors are classified into retry-relevant categories before budget reduction retries.
- Evidence: `src/lms_llmsTxt/retry_policy.py`

3. Output sanitization strips reasoning/thinking tags and common prefixes before writing artifacts.
- Evidence: `src/lms_llmsTxt/reasoning.py`

4. HyperGraph route handlers translate internal errors into user-facing error strings rather than leaking stack traces.
- Evidence: `hypergraph/app/api/generate/route.ts`

### Recommended

1. Continue classifying errors before retrying to avoid blind retry loops.
2. Keep sanitization in the write path (not only at display time) to preserve artifact safety in downstream tools.
3. When adding new UI modes, preserve the simple error response contract unless all clients are updated together.

## 6. Documentation and Operational Standards

### Discovered

1. The repo uses layered documentation:
- top-level `README.md` for install/usage
- `docs/` for architecture and operational guides
- `hypergraph/README.md` for the UI app

2. Documentation includes executable path examples using real artifact paths and MCP URI examples.
- Evidence: `README.md`, `docs/getting-started.md`

3. Reliability validation notes are documented in README with concrete run outcomes.
- Evidence: `README.md`

### Recommended

1. Keep interface docs close to implementation changes (CLI flags, MCP resources, HyperGraph modes).
2. Update `docs/architecture.md`, `docs/standards.md`, and `docs/patterns.md` together when adding new subsystems.
3. Maintain a review checklist for low-confidence or environment-specific claims after major refactors.

## 7. Explicitly Excluded from This Pass

1. Test suite conventions and test architecture (user-directed exclusion).
2. CI/CD workflow internals and deployment infrastructure (not fully represented in repo code).
3. Vendor and generated content in `artifacts/`, `node_modules/`, `.next/`, `.ck/`.
