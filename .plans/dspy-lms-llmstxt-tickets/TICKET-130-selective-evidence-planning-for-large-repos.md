---
ticket_id: "tkt_lmsllmstxt_selective_evidence"
title: "Large repositories are analyzed through selective evidence planning before compaction"
agent: "codex"
done: false
goal: "Repository analysis selects high-value evidence for deeper inspection before relying on deterministic compaction, especially for large repositories."
---

## Tasks
- Add a DSPy evidence-selection module that ranks candidate directories, docs, files, and examples using the repo digest plus lightweight metadata.
- Fetch deeper content only for selected high-value candidates.
- Enforce hard limits on candidate count, bytes per fetch, recursion depth, and total exploration budget.
- Use `RepoDigest` as a routing input for likely documentation roots, real entry points, subsystem boundaries, and deeper evidence fetch decisions.
- Keep deterministic budget enforcement and compaction as safety rails, but move compaction behind selective inspection.

## Acceptance criteria
- Default operation plans evidence before compaction on repositories that would otherwise exceed context limits.
- Budget controls remain enforced and compaction is retained as a last resort rather than the primary analysis strategy.
- Selected evidence and dropped evidence are traceable from the analyzer output.

## Tests
- Run generation on a large repository and verify deeper inspection is limited to selected candidates rather than full prompt stuffing.
- Run generation under a tight budget and verify compaction still occurs only after selective planning is attempted.
- Inspect trace output and verify selected evidence, dropped evidence, and budget-limit decisions are recorded.

## Notes
- Source: "Replace truncation-first analysis with staged evidence planning", "Compaction should become last resort, not primary strategy", "Use the digest to rank likely doc roots, find real entry points, detect subsystem boundaries, decide where more evidence should be fetched."
- Constraints:
  - Preserve deterministic safety rails around maximum fetch count and token budget.
  - Do not remove budget enforcement; move it later in the decision chain.
- Evidence:
  - `RepoDigest`
  - Current compaction and retry behavior described in the handoff
- Dependencies:
  - TICKET-100-repository-analyzer-staged-pipeline.md
  - TICKET-110-pin-and-audit-dspy-litellm-upgrade-path.md
- Unknowns:
  - Exact candidate-selection features and fetch interfaces are not provided.
