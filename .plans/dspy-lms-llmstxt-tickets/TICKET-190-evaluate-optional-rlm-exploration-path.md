---
ticket_id: "tkt_lmsllmstxt_rlm_eval"
title: "Optional RLM-style exploration path is evaluated for large-repository quality"
agent: "codex"
done: true
goal: "The team has a bounded evaluation of whether RLM-style recursive exploration improves llms.txt quality on large repositories."
---

## Tasks
- Evaluate an RLM-guided selective exploration path against the digest-plus-selective-inspection baseline for large or deeply nested repositories.
- Constrain exploration with hard limits on depth, file count, and total exploration budget.
- Compare output quality, latency, and token cost before deciding whether to adopt the path.

## Acceptance criteria
- The evaluation determines whether RLM improves large-repository output under bounded runtime and cost constraints.
- Any RLM path remains optional and does not replace deterministic budget enforcement or the fallback generator.
- Results are comparable against the current selective-planning baseline.

## Tests
- Run side-by-side large-repository comparisons for the RLM path and the selective-planning baseline.
- Verify hard exploration limits are enforced during the comparison.
- Record quality, latency, and token-cost comparison outputs for the evaluated repositories.

## Notes
- Source: "RLM is the most relevant addition", "Evaluate RLM only after the structured planner exists", "Constrain exploration depth and file count to preserve predictable runtime."
- Constraints:
  - Preserve predictable runtime through hard limits.
  - Keep RLM as an optional advanced path rather than the only generation path.
- Evidence:
  - DSPy RLM discussion in the handoff
  - `src/lms_llmsTxt/rlm_evaluation.py` defines optional deterministic RLM-style exploration scaffolding without adding dependencies or replacing fallback/deterministic paths.
  - `ExplorationLimits` enforces non-negative depth and positive file/character budgets.
  - `apply_exploration_limits(...)` enforces hard depth, file-count, and total-character limits and returns selected/skipped paths plus estimated token cost.
  - `evaluate_optional_rlm_path(...)` reuses the TICKET-170 benchmark comparison model and records quality, latency, and token deltas against the selective-planning baseline.
  - `tests/test_rlm_evaluation.py` verifies budget enforcement, digest-derived candidate priority/deduplication, side-by-side quality/cost comparison, and invalid limit rejection.
  - `uv run --extra test pytest -q tests/test_rlm_evaluation.py --tb=short` reported `6 passed, 12 warnings`.
  - `uv run --extra test pytest -q tests/test_rlm_evaluation.py tests/test_evaluation.py tests/test_analyzer.py tests/test_repo_digest.py --tb=short` reported `22 passed, 12 warnings`.
  - `uv run --extra test pytest -q --tb=short` reported `90 passed, 1 skipped, 18 warnings`.
- Dependencies:
  - TICKET-130-selective-evidence-planning-for-large-repos.md
  - TICKET-150-dspy-planned-llmstxt-synthesis-with-deterministic-rendering.md
  - TICKET-170-benchmark-and-evaluation-loop-for-llmstxt-quality.md
- Unknowns:
  - Exact external repository set for future live RLM evaluation is not provided; current evaluation is deterministic and fixture-driven.
  - Exact model-backed RLM integration surface remains optional and should not be adopted without further evidence.
