# Architecture Overview

This document explains how `lms-llmsTxt` is organized and how data moves from a repository URL to generated artifacts.

## System Design

## High-Level Flow

```text
User (CLI or MCP)
  -> Input validation/config
  -> Repository material collection (GitHub API)
  -> Budget preflight and compaction
  -> Analyzer generation (DSPy + LM Studio)
      -> primary path (normal)
      -> fallback path (resilient output)
  -> Optional graph build
  -> Artifact write + MCP resource exposure
```

## Core Components

1. `src/lms_llmsTxt/cli.py`
- CLI interface and runtime options.
- Maps command-line flags into `AppConfig` and `run_generation(...)`.

2. `src/lms_llmsTxt/pipeline.py`
- Main orchestration pipeline.
- Handles budget checks, retries, fallback behavior, sanitization, and output writing.

3. `src/lms_llmsTxt/analyzer.py`
- DSPy-based semantic extraction and markdown synthesis.
- Uses normalized predictor outputs so sparse model responses do not crash generation.

4. `src/lms_llmsTxt/repo_digest.py`
- Map/reduce style repository digest generation from file tree and repository content.

5. `src/lms_llmsTxt/graph_builder.py`
- Builds grounded graph artifacts:
  - `repo.graph.json`
  - `repo.force.json`
  - node markdown files

6. `src/lms_llmsTxt_mcp/server.py`
- FastMCP server entrypoint.
- Exposes generation tools and artifact resources for external agent clients.

7. `src/lms_llmsTxt_mcp/graph_resources.py`
- Graph resource discovery and URI mapping.
- Supports both `lmstxt://graphs/...` and `repo://{repo_id}/graph/nodes/{node_id}` access patterns.

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
    context_budget.py
    context_compaction.py
    retry_policy.py
    reasoning.py
    fallback.py
    github.py
    lmstudio.py
  lms_llmsTxt_mcp/
    server.py
    generator.py
    runs.py
    artifacts.py
    graph_resources.py
    session_memory.py
tests/
docs/
artifacts/
```

## Data Flow Details

1. Input and config
- CLI/MCP receives repository URL and options.
- `AppConfig` resolves defaults from env + CLI arguments.

2. Repository collection
- `github.py` gathers:
  - file tree
  - README
  - package/config file content
  - default branch + repo metadata

3. Budgeting and compaction
- `context_budget.py` estimates context usage.
- `context_compaction.py` shrinks oversized material before LLM invocation.

4. Generation
- Analyzer attempts primary DSPy path.
- `retry_policy.py` controls retries for context/provider failures.
- `fallback.py` guarantees usable output if primary generation fails.

5. Post-processing
- `reasoning.py` sanitizes output for hidden reasoning markers.
- `full_builder.py` optionally expands output to `llms-full.txt`.
- `graph_builder.py` generates graph artifacts when requested.

6. Persistence and serving
- Artifacts are written to `artifacts/<owner>/<repo>/`.
- MCP server exposes read/list interfaces for tools and resources.

## Key Design Decisions

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

## Extension Points

1. Add new fallback strategies in `fallback.py`.
2. Add provider/runtime controls in `lmstudio.py` and `config.py`.
3. Add new MCP tools/resources in `src/lms_llmsTxt_mcp/server.py`.
4. Add richer graph node semantics in `graph_builder.py` and `graph_models.py`.

## Testing Strategy

- Unit tests for normalization, budgeting, retry policy, and graph resources.
- MCP integration tests for stdio tool execution.
- E2E CLI validation against public repositories to verify artifact correctness and sanitization.
