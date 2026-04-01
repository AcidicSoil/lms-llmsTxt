---
ticket_id: "tkt_lmsllmstxt_benchmark_eval"
title: "Benchmark and evaluation loop can measure planner quality against repository outcomes"
agent: "codex"
done: false
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
- Dependencies:
  - TICKET-130-selective-evidence-planning-for-large-repos.md
  - TICKET-150-dspy-planned-llmstxt-synthesis-with-deterministic-rendering.md
- Unknowns:
  - Exact benchmark repository list is not provided.
  - Exact optimizer choice and tuning procedure are not provided.
