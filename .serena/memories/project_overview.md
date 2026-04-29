# Project Overview
- Purpose: Generate `llms.txt`, `llms-full.txt`, optional `llms-ctx.txt`, fallback JSON, and optional graph artifacts for GitHub repositories using DSPy with LM Studio.
- Primary runtime: Python package under `src/lms_llmsTxt` with CLI entrypoint `lmstxt` and MCP server package under `src/lms_llmsTxt_mcp` with entrypoint `lmstxt-mcp`.
- Secondary runtime: HyperGraph UI under `hypergraph/`, driven through root `package.json` scripts.
- Core generation flow: `src/lms_llmsTxt/pipeline.py` orchestrates repository fetch, context budgeting/compaction, digest building, analyzer execution, fallback generation, artifact writes, graph emission, and optional session-memory append.
- Analyzer surface: `src/lms_llmsTxt/analyzer.py` currently mixes DSPy analysis, light digest handling, bucket generation, and deterministic markdown rendering.
- Tests: pytest suite under `tests/` covers analyzer, pipeline-adjacent behavior, LM Studio integration, graph generation, MCP server/resources, retry policy, and context budgeting.
- Packaging: Python metadata in `pyproject.toml`; root `package.json` is mainly for HyperGraph/codefetch scripts.
