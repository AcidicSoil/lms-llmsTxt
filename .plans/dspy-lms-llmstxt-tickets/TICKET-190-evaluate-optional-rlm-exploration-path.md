---
ticket_id: "tkt_lmsllmstxt_rlm_eval"
title: "Optional RLM-style exploration path is evaluated for large-repository quality"
agent: "codex"
done: false
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
- Dependencies:
  - TICKET-130-selective-evidence-planning-for-large-repos.md
  - TICKET-150-dspy-planned-llmstxt-synthesis-with-deterministic-rendering.md
  - TICKET-170-benchmark-and-evaluation-loop-for-llmstxt-quality.md
- Unknowns:
  - Exact repository set for RLM evaluation is not provided.
  - Exact RLM integration surface is not provided.
