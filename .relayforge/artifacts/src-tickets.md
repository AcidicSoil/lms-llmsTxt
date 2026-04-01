```md
# path: TICKET-110-analyzer-ir-staged-pipeline.md
---
ticket_id: "tkt_analyzer_ir_stage_01"
title: "Expose analyzer decisions through a staged IR pipeline"
agent: "codex"
done: false
goal: "The analyzer runs through explicit, typed intermediate stages so intermediate decisions can be inspected, tested, and persisted independently."
---

## Tasks
- Extract `RepositoryAnalyzer.forward()` into explicit stage boundaries that match the reviewed target flow: `RepoDigest -> EvidencePlan -> EvidenceSet -> SectionPlan -> LlmsDocument -> Renderer`.
- Introduce typed IR dataclasses for the stage outputs, including the reviewed examples `EvidencePlan`, `EvidenceSet`, `SectionPlan`, and `LlmsDocument`.
- Convert each stage into a pure function or equivalent side-effect-free unit with explicit inputs and outputs.
- Add logging hooks and optional persistence points for stage artifacts without changing final rendering semantics beyond the refactor.
- Preserve the existing fallback path while routing it through the new stage boundaries where applicable.

## Acceptance criteria
- Analyzer execution no longer performs repo analysis, structure analysis, fallback logic, example generation, bucket building, and markdown rendering inside a single monolithic method.
- Each named stage has a typed output that can be inspected independently in tests or logs.
- Intermediate stage outputs can be logged and optionally persisted without requiring ad hoc introspection inside `forward()`.
- Existing fallback behavior remains available and isolated after the refactor.

## Tests
- Run the analyzer test suite and confirm the refactored pipeline passes existing behavior checks.
- Add or update tests that exercise each stage independently with typed IR assertions.
- Add a verification test or explicit check that stage artifacts can be emitted to logs or persisted when enabled.

## Notes
- Source: "Critical — Analyzer pipeline is fake-structured but effectively monolithic" and "Break into explicit stages with typed IR".
- Constraints: Do not add new planning behavior in this ticket beyond introducing explicit stages and typed IR.
- Evidence: `RepositoryAnalyzer.forward()` currently performs repo analysis, structure analysis, fallback logic, example generation, bucket building, and markdown rendering in one method.
- Dependencies: Not provided.
- Unknowns: Exact persistence format for stage artifacts is not provided.
```

```md
# path: TICKET-120-dspy-section-planner-authority.md
---
ticket_id: "tkt_dspy_section_plan_01"
title: "Make DSPy authoritative for section planning"
agent: "codex"
done: false
goal: "DSPy determines section inclusion, ordering, and planning, while code remains responsible for validated markdown rendering."
---

## Tasks
- Route final document construction through a `SectionPlan` produced by DSPy instead of relying on ignored or side-effect-only model calls.
- Promote the model's responsibility to section planning only: sections, ordering, and inclusion.
- Keep markdown formatting deterministic in code by rendering from the validated section plan.
- Resolve the currently non-authoritative DSPy modules by either wiring them into the planner path or removing them when they have no effect on output.
- Add schema validation or equivalent constraints around DSPy planner output before rendering.

## Acceptance criteria
- Final output is planned from a DSPy-produced section plan rather than bypassing DSPy in favor of a purely deterministic end-to-end renderer.
- `GenerateUsageExamples` and `GenerateLLMsTxt` are no longer dead or ignored paths; each is either integrated into the authoritative planning flow or removed.
- The planner can affect visible document structure without taking over markdown formatting.
- Invalid planner output is constrained or rejected by explicit validation before rendering.

## Tests
- Add or update tests showing that changing DSPy planner output changes section selection or ordering in the rendered document.
- Add validation tests for malformed or incomplete planner output.
- Run the analyzer and rendering test suite to confirm deterministic formatting remains stable when fed the same section plan.

## Notes
- Source: "DSPy calls are mostly non-authoritative" and "Make DSPy authoritative at section planning level, not formatting".
- Constraints: Keep code authoritative for markdown formatting; do not expand DSPy authority beyond planning in this ticket.
- Evidence: `GenerateUsageExamples` output is ignored, `GenerateLLMsTxt` is not used for final output, and final output is currently rendered by deterministic markdown code.
- Dependencies: `TICKET-110-analyzer-ir-staged-pipeline.md`.
- Unknowns: Whether DSPy should become the primary planner or remain an enhancer was identified as the highest ambiguity in the review.
```

```md
# path: TICKET-130-selective-evidence-planning.md
---
ticket_id: "tkt_selective_evidence_01"
title: "Select repository evidence before compaction"
agent: "codex"
done: false
goal: "Large-repository context is built from selectively ranked evidence instead of uniform truncation and proportional shrinking."
---

## Tasks
- Replace truncation-first context assembly with selective evidence planning that ranks candidate inputs before fetching or compacting them.
- Implement candidate ranking around the reviewed priorities: entry points, docs, and high-centrality paths.
- Fetch only the top-ranked evidence needed for planning and rendering.
- Retain compaction as a last-resort fallback instead of the primary budgeting mechanism.
- Update retry behavior so it does not reduce all sources uniformly without semantic priority.

## Acceptance criteria
- Context budgeting no longer starts with hard truncation of file tree lines, README content, and package files.
- Evidence selection distinguishes important files from noise before compaction is applied.
- Large repositories can preserve prioritized entry points and documentation instead of dropping them arbitrarily.
- Compaction remains available only after ranked evidence selection is exhausted or still exceeds budget.

## Tests
- Add or update tests that verify ranked evidence survives budget pressure ahead of lower-priority material.
- Add a regression test covering a large-repository input where important entry points are retained.
- Run the context-budgeting and analyzer test suites to confirm retry behavior no longer applies uniform shrinking first.

## Notes
- Source: "Replace with selective evidence planning (your TICKET-130)" and "Compaction as last resort only".
- Constraints: Do not remove compaction entirely; keep it as a fallback.
- Evidence: Current budgeting uses hard truncation, proportional shrinking, and uniform retry reduction.
- Dependencies: `TICKET-110-analyzer-ir-staged-pipeline.md`, `TICKET-120-dspy-section-planner-authority.md`.
- Unknowns: Exact ranking heuristics or whether ranking should use heuristics versus a DSPy module is not provided.
```

```md
# path: TICKET-140-url-validation-latency-hardening.md
---
ticket_id: "tkt_url_validation_fix_01"
title: "Eliminate synchronous per-URL validation from bucket building"
agent: "codex"
done: false
goal: "URL handling no longer serially probes each page with unbounded synchronous requests that add latency, fragility, and silent data loss."
---

## Tasks
- Remove URL liveness probing as the default behavior in bucket building, or replace it with a bounded strategy that avoids serial synchronous validation.
- If validation is retained, implement batch or concurrent validation, cache results, and soft-fail instead of dropping URLs silently.
- Ensure invalid or flaky URL checks do not silently remove output links without marking their status.
- Add explicit limits around network probing so real repositories with many URLs do not trigger unbounded latency.

## Acceptance criteria
- Bucket building no longer performs serial HEAD/GET validation per page by default.
- URL handling does not silently drop links solely because liveness checks are flaky.
- Any retained validation path is bounded and avoids the current synchronous per-URL latency trap.
- Output behavior under dead or slow links is explicit and testable.

## Tests
- Add or update tests for bucket building with many URLs to verify latency-sensitive behavior does not rely on serial probing.
- Add tests covering flaky or dead URLs to confirm soft-fail handling and link retention or marking behavior.
- Run the relevant pipeline tests to confirm URL-heavy inputs no longer trigger the current drop-on-failure pattern.

## Notes
- Source: "URL validation is a latency and reliability trap" and "Remove validation by default".
- Constraints: Accept including dead links if needed to avoid the current performance and reliability cost.
- Evidence: `_url_alive()` performs HEAD then fallback GET and is called per page in bucket building with no concurrency or caching.
- Dependencies: `TICKET-110-analyzer-ir-staged-pipeline.md`.
- Unknowns: Not provided.
```

```md
# path: TICKET-150-cli-runtime-boundaries.md
---
ticket_id: "tkt_cli_runtime_split_01"
title: "Separate CLI argument parsing from runtime orchestration"
agent: "codex"
done: false
goal: "CLI behavior is split into clear modules so argument parsing, pipeline orchestration, and UI lifecycle can evolve and be tested independently."
---

## Tasks
- Reduce `cli.py` to argument parsing and command dispatch only.
- Move pipeline orchestration into `app.py`.
- Move UI server lifecycle, subprocess handling, and browser launch behavior into `ui_runtime.py`.
- Update the invocation path so CLI UX remains intact while side-effecting runtime concerns live outside the parser module.

## Acceptance criteria
- `cli.py` no longer mixes argument parsing with runtime configuration, pipeline execution, UI server startup, subprocess management, and browser opening.
- Orchestration logic is reusable programmatically without importing CLI-only behavior.
- UI lifecycle concerns are isolated from business logic and parser code.
- The user-facing CLI entrypoint still works after the split.

## Tests
- Add or update tests for CLI argument parsing independent of runtime side effects.
- Add or update orchestration tests that run without browser-launch or subprocess side effects.
- Run the CLI test suite and an end-to-end CLI smoke check after the module split.

## Notes
- Source: "CLI is doing orchestration + infra + UX" and recommended split into `cli.py`, `app.py`, and `ui_runtime.py`.
- Constraints: Preserve existing CLI behavior while separating responsibilities.
- Evidence: `cli.py` currently parses args, configures runtime, runs the pipeline, starts a UI server, manages subprocesses, and opens a browser.
- Dependencies: Not provided.
- Unknowns: Exact command surface and module boundaries beyond the reviewed split are not provided.
```

```md
# path: TICKET-160-graph-authoritative-structure-layer.md
---
ticket_id: "tkt_graph_llmstxt_align_01"
title: "Use the repository graph as the structure layer for llms.txt planning"
agent: "codex"
done: false
goal: "The graph and llms.txt pipelines share one structural model so graph information can drive planning, coverage checks, and output consistency."
---

## Tasks
- Integrate graph structure into the llms.txt planning flow instead of maintaining disconnected parallel representations.
- Use graph clusters or equivalent graph-derived structure as an input to section planning.
- Ensure llms.txt output can reference graph nodes or graph-derived structure where relevant.
- Add evaluation or validation that uses graph coverage rather than leaving the graph pipeline unused by output generation.

## Acceptance criteria
- llms.txt planning consumes graph structure rather than ignoring the graph pipeline.
- The graph is no longer a disconnected parallel representation of repository structure.
- Section planning or coverage validation demonstrably uses graph-derived information.
- Structural duplication between `RepoDigest` usage and graph-building is reduced or made explicit.

## Tests
- Add or update tests showing graph-derived structure influences section planning or coverage validation.
- Add a regression test confirming graph integration does not leave llms.txt output semantically disconnected from the graph pipeline.
- Run analyzer, graph, and output-generation tests after integration.

## Notes
- Source: "Graph pipeline is disconnected from llms.txt" and "Use graph as authoritative structure layer".
- Constraints: Do not invent new graph semantics beyond section planning, llms.txt references, and evaluation uses explicitly called out in the review.
- Evidence: `RepoDigest` is used in the analyzer and `graph_builder` builds a graph from the same digest, but llms.txt does not consume graph structure and graph does not influence output.
- Dependencies: `TICKET-110-analyzer-ir-staged-pipeline.md`, `TICKET-120-dspy-section-planner-authority.md`.
- Unknowns: Graph usage intent was inferred from structure, not documentation.
```

```md
# path: TICKET-190-review-architecture-direction.md
---
ticket_id: "tkt_user_review_dspy_01"
title: "Confirm planner authority and review the decomposed architecture changes"
agent: "user"
done: false
goal: "A human review records whether DSPy should be the primary planner or remain an enhancer and confirms the staged architecture matches intended direction."
---

## Tasks
- Review the staged analyzer, DSPy planning, evidence selection, URL handling, CLI split, and graph integration changes against the source review.
- Decide whether DSPy is intended to be the primary decision-maker for planning or whether deterministic heuristics should remain dominant with DSPy as an enhancer.
- Confirm whether any conflicting implementation choices diverge from the review's intended tradeoffs and priorities.

## Acceptance criteria
- A human decision is recorded for DSPy planner authority versus heuristic dominance.
- The decomposed tickets are verified as covering the review's actionable items without hidden dependencies.
- Any unresolved architectural disagreement is explicitly called out rather than left implicit.

## Tests
- Review the implemented outputs and confirm the recorded architecture choice matches the intended direction.
- Verify each completed lower-numbered ticket can be evaluated against this review without missing scope.

## Notes
- Source: "One question (targeting highest ambiguity)" and the listed priority order under "What to change first".
- Constraints: Do not resolve the DSPy authority ambiguity implicitly through code alone.
- Evidence: The review states ambiguity score 0.38 and identifies planner authority as the main uncertainty.
- Dependencies: `TICKET-120-dspy-section-planner-authority.md`, `TICKET-130-selective-evidence-planning.md`, `TICKET-140-url-validation-latency-hardening.md`, `TICKET-150-cli-runtime-boundaries.md`, `TICKET-160-graph-authoritative-structure-layer.md`.
- Unknowns: Final architecture preference is not provided in the source review.
```

[tickets.zip](sandbox:/mnt/data/tickets.zip)

