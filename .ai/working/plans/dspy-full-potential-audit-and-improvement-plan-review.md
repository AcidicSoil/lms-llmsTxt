# Plan Review: DSPy Full-Potential Audit and Improvement Plan

> **To apply fixes:** Open new session, run:
> `Read this file, then apply the suggested fixes to .plans/dspy-full-potential-audit-and-improvement-plan.md`

**Reviewed:** 2026-05-13
**Verdict:** With fixes (1-6)

---

## Plan Review: DSPy Full-Potential Audit and Improvement Plan

**Plan:** `.plans/dspy-full-potential-audit-and-improvement-plan.md`  
**Tech Stack:** Python, DSPy 3.2.0, pytest, requests/LM Studio, optional observability/retrieval backends

### Summary Table

| Criterion | Status | Notes |
|-----------|--------|-------|
| Parallelization | ⚠️ ISSUES | Phases are mostly sequential and sensible, but independent workstreams and critical path are not explicit. |
| TDD Adherence | ⚠️ ISSUES | Validation exists, but ticket-level RED/GREEN steps and failing-test checkpoints are missing. |
| Type/API Match | ⚠️ ISSUES | `Literal[entrypoint, ...]` is not valid Python typing syntax, and new capsule fields are not reconciled with the existing `ChunkCapsule` dataclass. |
| Library Practices | ⚠️ ISSUES | Plan references `dspy.Assert`/`dspy.Suggest`, but local DSPy guidance says these are removed in DSPy 3.x; project pins `dspy-ai==3.2.0`. |
| Security/Edge Cases | ⚠️ ISSUES | Good budget/fallback controls are stated, but model-output validation, dependency-gated optional integrations, and prompt-injection handling need ticket-level acceptance criteria. |

### Evidence Checked

- `pyproject.toml` pins `dspy-ai==3.2.0` and pytest 9.0.3.
- `src/lms_llmsTxt/repo_digest.py` contains `_extract_symbols`, `_extract_dependencies`, `_summarize`, `_path_priority`, `plan_evidence_paths`, and `extract_chunk_capsules`; the current `ChunkCapsule` fields are `chunk_id`, `path`, `chunk_type`, `summary`, `key_symbols`, and `dependencies`.
- `src/lms_llmsTxt/analyzer.py` contains `_short_note`, `_score`, and `TAXONOMY` path-based section logic.
- `src/lms_llmsTxt/graph_builder.py` contains `_subsystem_relation_score` and `_related_edges` heuristic edge selection.
- `src/lms_llmsTxt/graph_dspy_synthesizer.py` uses `dspy.ChainOfThought(SynthesizeRepoGraphNodes)`.
- `src/lms_llmsTxt/graph_semantic_synthesizer.py` uses direct `requests.post` LM Studio calls and custom streaming parsing.

### Issues Found

#### Critical (Must Fix Before Execution)

1. [Opportunity 5, lines 235 and 243] DSPY3_REMOVED_ASSERTIONS
   - Issue: The plan recommends `dspy.Assert`/`dspy.Suggest` for new work.
   - Why: The repo pins `dspy-ai==3.2.0`, and the local `dspy-assertions` skill states these APIs were removed in DSPy 3.x. Implementing this as written risks immediate runtime/API failure or wasted work.
   - Fix: Replace assertion guidance with `dspy.Refine`, `dspy.BestOfN`, deterministic validators, and reward functions.
   - Suggested edit:
   ```markdown
   Use `dspy.Refine` or `dspy.BestOfN` for nodes that fail validation. Keep deterministic validators as the hard gate before replacing output, and express generic-heading/boilerplate penalties through a reward function or judge score. Do not use `dspy.Assert` or `dspy.Suggest`; they are not available in DSPy 3.x.
   ```

#### Major (Should Fix)

2. [Opportunity 1, lines 68-75] INVALID_LITERAL_AND_CAPSULE_SCHEMA_GAP
   - Issue: `role: Literal[entrypoint, domain, ...]` is not valid Python typing syntax, and the plan adds `domain_terms`, `role`, and `confidence` without saying whether `ChunkCapsule` changes or whether a model-only capsule is mapped back to the current dataclass.
   - Why: `ChunkCapsule` currently has no `domain_terms`, `role`, or `confidence`; downstream `reduce_capsules()` expects the existing fields. Ambiguous schema evolution will cause implementation churn or silent loss of model outputs.
   - Fix: Use quoted `Literal` values and explicitly choose either an expanded internal dataclass or a separate DSPy output object with deterministic mapping into `ChunkCapsule`.
   - Suggested edit:
   ```markdown
   Add `ExtractRepoChunkCapsule(dspy.Signature)` with Python-compatible field types:

   - `summary: str`
   - `symbols: list[str]`
   - `dependencies: list[str]`
   - `domain_terms: list[str]`
   - `role: Literal["entrypoint", "domain", "adapter", "config", "test", "docs", "generated", "asset"]`
   - `confidence: float`

   Implementation note: keep the existing `ChunkCapsule` contract stable for `reduce_capsules()` initially. Store `domain_terms`, `role`, and `confidence` in an extended internal capsule/metadata sidecar, or explicitly extend `ChunkCapsule` and update all consumers in the same ticket.
   ```

3. [Phase 1 / recommended slice, lines 453-457 and 535-539] DEPENDENCY_ORDER_MISMATCH
   - Issue: Phase 1 says implement `ExtractRepoChunkCapsule` and `RankEvidenceCandidates`, but the recommended first slice is `TICKET-DSPY-001 + TICKET-DSPY-020`, skipping `TICKET-DSPY-010` typed capsules.
   - Why: The reranker is described as ranking over digest/candidate metadata and later retrieval over capsules/excerpts. Implementing `020` first may force the reranker to depend on the current weak regex/truncation metadata, limiting the value being measured.
   - Fix: Make the first slice either `001 + 010` or define `020` as path-only v0 with explicit limitations and a follow-up to consume typed capsules.
   - Suggested edit:
   ```markdown
   Start with **TICKET-DSPY-001 + TICKET-DSPY-010**, then implement **TICKET-DSPY-020** once typed capsule metadata exists.

   Alternative: implement **TICKET-DSPY-020a** as a path-only reranker baseline, with explicit acceptance criteria that **020b** must consume typed capsule fields from **010** before rollout.
   ```

4. [Immediate tickets, lines 518-533] TDD_STEPS_MISSING
   - Issue: Tickets name validation outcomes but do not specify tests written before implementation, expected failing commands, or minimal green implementation checkpoints.
   - Why: The plan is broad enough that implementation could drift into large, untested AI rewrites. The review-plan skill specifically requires RED/GREEN discipline for each task.
   - Fix: Add per-ticket acceptance criteria with initial failing tests and exact pytest commands.
   - Suggested edit:
   ```markdown
   For each ticket, add:

   - RED: add/extend a focused test that fails against current behavior.
   - Verify failure: run `uv run pytest <test-file>::<test-name>` and record the failing assertion.
   - GREEN: implement the smallest feature-flagged change that passes the focused test.
   - Regression: run the relevant existing test file and confirm default behavior remains unchanged when the feature flag is disabled.
   ```

5. [Opportunity 8, lines 336-364] OPTIONAL_OBSERVABILITY_DEPENDENCIES_UNSPECIFIED
   - Issue: The plan lists MLflow, Phoenix, Langfuse, Langwatch, Langtrace, and Weave but does not define extras, lazy imports, or dependency isolation.
   - Why: `pyproject.toml` currently has only `dev` and `test` extras. Adding trace integrations directly can bloat installs or break import-time behavior, despite the plan’s “no import-time dependency” test goal.
   - Fix: Specify extras and a common adapter interface before implementing backends.
   - Suggested edit:
   ```markdown
   Add observability integrations only behind optional extras and lazy imports, for example `observability-mlflow`, `observability-phoenix`, and `observability-langfuse`. The core package must import successfully without these extras installed. Define a small internal `TraceSink` protocol before adding backend-specific adapters.
   ```

6. [Opportunity 6 / Phase 5, lines 264-273 and 497-506] RETRIEVAL_AND_PARALLELISM_EDGE_CASES_UNDERDEFINED
   - Issue: Retrieval and async/parallel enrichment are promising, but the plan does not define cache keys, cancellation/timeout behavior, duplicate fetch prevention, or deterministic ordering of parallel results.
   - Why: Parallel model calls and retrieval can make outputs nondeterministic, exceed budgets, or reorder evidence in ways that destabilize artifacts and tests.
   - Fix: Add runtime invariants for retrieval and parallel execution before implementation.
   - Suggested edit:
   ```markdown
   Runtime invariants for retrieval/parallel work:

   - stable candidate IDs and deterministic final ordering after parallel completion
   - per-module timeout and global run timeout
   - max concurrent LM calls and max total calls per artifact
   - cache key includes repo digest ID, path, chunk range, artifact goal, model policy version, and signature version
   - duplicate candidate/path fetches are coalesced
   - timeout/failure falls back to deterministic ranking without partial malformed model output
   ```

#### Minor (Nice to Have)

7. [Skill coverage matrix, lines 14-26] SKILL_COVERAGE_TOO_BROAD
   - Issue: The skill matrix reads as a comprehensive inventory rather than applied implementation guidance.
   - Fix: Move the broad list to an appendix and keep only skills directly used by each ticket in the ticket body.

8. [Opportunity 9, lines 377-380] RETIREMENT_DECISION_CRITERIA_MISSING
   - Issue: The plan says port or retire `graph_semantic_synthesizer.py`, but does not define how to decide.
   - Fix: Add decision criteria such as feature parity, test coverage, streaming requirement, quality comparison, and migration/removal steps.

9. [Opportunity 10, lines 408-426] MODEL_ROUTING_POLICY_NEEDS_DEFAULT-SAFE CONTRACT
   - Issue: Model routing has good intent but no explicit “single configured model remains the default” acceptance test.
   - Fix: Add a regression test proving current model selection behavior is unchanged unless a routing feature flag is enabled.

### Parallelization Notes

Recommended execution batches after fixes:

1. **Batch A: Baseline and test scaffolding**
   - TICKET-DSPY-001
   - benchmark fixture design
   - per-ticket RED tests

2. **Batch B: Independent foundations**
   - TICKET-DSPY-010 typed capsules
   - observability interface/extras scaffolding
   - semantic graph port/retire decision tests

3. **Batch C: Consumers of better metadata**
   - TICKET-DSPY-020 evidence reranker
   - TICKET-DSPY-030 section classifier
   - TICKET-DSPY-040 graph relation inference

4. **Batch D: Quality and optimization loop**
   - TICKET-DSPY-050 node refinement
   - TICKET-DSPY-060 optimizer harness

5. **Batch E: Runtime scale**
   - TICKET-DSPY-070 tracing backend
   - async/parallel enrichment
   - model routing

Maximum safe concurrency: 2-3 agents after Batch A, provided each ticket owns separate files and feature flags. Critical path: baseline metrics → typed capsules/evidence metadata → reranker/section/graph modules → refinement/optimization → runtime scaling.

### Verdict

**Ready to execute?** With fixes (1-6)

**Reasoning:** The plan correctly identifies high-value DSPy underuse and preserves deterministic guards, but it should not be executed as-is because it contains a DSPy 3.x API incompatibility, schema ambiguity, dependency-order drift, and insufficient ticket-level TDD/runtime invariants.
