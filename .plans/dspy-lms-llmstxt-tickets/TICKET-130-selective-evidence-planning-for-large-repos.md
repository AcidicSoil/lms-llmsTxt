---
ticket_id: "tkt_lmsllmstxt_selective_evidence"
title: "Large repositories are analyzed through selective evidence planning before compaction"
agent: "codex"
done: true
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

## Completion evidence
- `src/lms_llmsTxt/repo_digest.py` defines `EvidencePlan` budget metadata and `EvidenceFetchLimits` for bounded selected-evidence fetching.
- `apply_evidence_plan()` can fetch deeper content only for selected paths through an injected `fetch_content` callback while enforcing fetch count, bytes-per-fetch, total-byte, and path-depth limits.
- `src/lms_llmsTxt/pipeline.py` applies selective evidence planning before deterministic compaction when the initial context budget is not approved, and fetches selected path content using the existing GitHub content fetcher.
- Analyzer trace entries now mark selected evidence with `content_fetched` and record fetch skips separately from budget-dropped evidence.
- `tests/test_repo_digest.py` covers bounded selected-content fetching and budget limits.
- `tests/test_lmstudio.py` verifies pipeline selective evidence planning happens before compaction and trace output records fetched content.
- `uv run --extra test pytest -q tests/test_repo_digest.py tests/test_lmstudio.py` reported `13 passed, 1 warning`.
- `uv run --extra test pytest -q` reported `73 passed, 1 skipped, 6 warnings`; the skip is the LM Studio/GitHub credential integration path.

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
