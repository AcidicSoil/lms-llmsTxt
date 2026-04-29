---
ticket_id: "tkt_lmsllmstxt_benchmark_eval"
title: "Benchmark and evaluation loop can measure planner quality against repository outcomes"
agent: "codex"
done: true
goal: "A benchmark and evaluation workflow exists to compare llms.txt quality before optimizer work is introduced."
---

## Tasks
- Build a benchmark set of repositories with desired `llms.txt` output characteristics.
- Define evaluation metrics for onboarding usefulness, API coverage quality, doc-link precision, redundancy penalty, and large-repository resilience.
- Use emitted graph artifacts as evaluation scaffolding for subsystem coverage, hotspot alignment, and omission checks.
- Gate DSPy optimizer work so it starts only after section planning and synthesis are model-controlled.

## Acceptance criteria
- Benchmark repositories and evaluation metrics exist for comparing the current heuristic path against the refactored DSPy-native path.
- Graph artifacts are usable in the evaluation workflow.
- Optimizer work is explicitly gated on the DSPy-native planner and synthesizer rather than the old deterministic renderer.

## Tests
- Run the benchmark workflow on baseline and refactored paths and produce comparable evaluation outputs.
- Exercise graph-based coverage checks and verify they can surface omissions on large or multi-subsystem repositories.

## Notes
- Source: "Build a benchmark set of repositories", "Define metrics", "Graph generation can become evaluation scaffolding", "Do not optimize until section planning and evidence selection are model-controlled."
- Constraints:
  - Optimizer work should not start before final content decisions move into DSPy.
- Evidence:
  - Existing graph artifact emission
  - Proposed metrics listed in the handoff
  - `src/lms_llmsTxt/evaluation.py` defines deterministic benchmark repository expectations, metrics, graph coverage/omission checks, and baseline/candidate comparison outputs.
  - `tests/test_evaluation.py` verifies metric scoring, graph-based omission surfacing, redundancy penalties, large-repository resilience, and comparable baseline/candidate score deltas.
  - `uv run --extra test pytest -q tests/test_evaluation.py --tb=short` reported `3 passed, 12 warnings`.
  - `uv run --extra test pytest -q tests/test_evaluation.py tests/test_graph_builder.py tests/test_analyzer.py tests/test_repo_digest.py --tb=short` reported `17 passed, 12 warnings`.
  - `uv run --extra test pytest -q --tb=short` reported `84 passed, 1 skipped, 18 warnings`.
- Dependencies:
  - TICKET-130-selective-evidence-planning-for-large-repos.md
  - TICKET-150-dspy-planned-llmstxt-synthesis-with-deterministic-rendering.md
- Unknowns:
  - Exact external benchmark repository list is not provided; current benchmark cases are deterministic in-repo fixtures.
  - Exact optimizer choice and tuning procedure are not provided and remain gated to TICKET-190+ work.
