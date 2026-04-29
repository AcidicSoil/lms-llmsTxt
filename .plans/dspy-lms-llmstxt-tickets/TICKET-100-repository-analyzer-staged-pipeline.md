---
ticket_id: "tkt_lmsllmstxt_stage_pipeline"
title: "Repository analysis runs through explicit planning and synthesis stages"
agent: "codex"
done: true
goal: "Repository analysis is split into explicit, inspectable stages with a structured intermediate representation while the existing product surface remains compatible."
---

## Tasks
- Split `RepositoryAnalyzer.forward()` into explicit internal stages for evidence planning, evidence inspection, section planning, synthesis, and rendering.
- Introduce a structured intermediate representation for final `llms.txt` content so the renderer consumes section and entry data instead of raw local buckets only.
- Remove unused DSPy calls or wire them into outputs; explicitly resolve the non-authoritative use of `GenerateLLMsTxt` and `GenerateUsageExamples`.
- Add trace logging or trace artifacts for selected evidence, dropped evidence, the final section plan, and reasons for compaction.

## Acceptance criteria
- CLI surface and flags, artifact naming and directory structure, graph artifact emission, fallback heuristic generation, FastMCP server contract, session-memory append-only behavior, and the LM Studio integration boundary remain compatible.
- The final renderer consumes the structured intermediate representation.
- The fallback path still emits artifacts when LM connectivity or generation fails.
- Internal stages and trace outputs are inspectable without relying on the previous monolithic `RepositoryAnalyzer.forward()` flow.

## Tests
- Run the existing CLI generation flow on a representative repository and verify artifact names and layout are unchanged.
- Exercise the fallback path by simulating LM failure and verify fallback artifacts are still emitted.
- Inspect the generated trace output and verify it includes selected evidence, dropped evidence, section planning, and compaction rationale.

## Completion evidence
- `src/lms_llmsTxt/analyzer.py` splits `RepositoryAnalyzer.forward()` into staged helpers for repository analysis, evidence planning, evidence inspection, usage-section building, section planning, and rendering.
- `src/lms_llmsTxt/models.py` defines the structured `LLMsDocument`, `LLMsSection`, and `LLMsLinkEntry` intermediate representation consumed by `render_llms_markdown()`.
- `GenerateUsageExamples` is wired into the emitted Usage section; `GenerateLLMsTxt` is not present in `src/` and no longer remains as an unused signature.
- `AnalyzerTrace` captures selected evidence, dropped evidence, section planning, model/deterministic section planning, and compaction reasons; `pipeline.py` writes the trace artifact and returns `trace_path`.
- `uv run --extra test pytest -q` reported `71 passed, 1 skipped, 6 warnings`; the skip is the LM Studio/GitHub credential integration test when the configured GitHub token is invalid or unauthorized.

## Notes
- Source: "Split `RepositoryAnalyzer.forward()` into smaller internal steps", "Remove unused DSPy calls or wire them into outputs", "Make the final renderer consume a structured intermediate representation", "Add explicit trace logging".
- Constraints:
  - Do not change the CLI surface or flags.
  - Do not change artifact naming or directory structure.
  - Do not rewrite the FastMCP server.
  - Do not collapse the fallback generator into the DSPy path.
- Evidence:
  - `RepositoryAnalyzer.forward()`
  - `GenerateLLMsTxt`
  - `GenerateUsageExamples`
  - `render_llms_markdown`
- Dependencies: Not provided
- Unknowns:
  - Exact file paths for the analyzer, renderer, and trace artifact locations are not provided.
