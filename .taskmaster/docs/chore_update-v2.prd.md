1. Overview

Problem statement: The lmstxt generator currently uses DSPy “core primitives” (a `dspy.Module` with `ChainOfThought(...)` calls returning a `Prediction`) and does not leverage DSPy’s newer optimizer/eval workflow, caching/async patterns, or adapter-based structured outputs. This leads to (a) nondeterministic, hard-to-parse analysis artifacts, (b) avoidable latency/cost from repeated calls, and (c) limited ability to systematically improve prompt/program quality with measurable metrics.

Target users:

* Repo maintainers and staff engineers who need consistent, machine-readable summaries (purpose, concepts, constraints) to feed downstream tooling (PRD/task generation, docs, agent loops).
* Tooling/automation engineers who want reliable, schema-valid outputs and a repeatable optimization workflow.

Why current solutions fail:

* Free-text outputs are brittle for downstream automation (parsing, validation, regression testing).
* Without caching and async execution, repeated runs are slower and more expensive than necessary.
* Without optimizer/evaluation integration, prompt/program improvements are ad hoc rather than metric-driven.

Success metrics:

* Structured-output validity: ≥ 99% of runs produce schema-valid analysis artifacts without manual fixes.
* Determinism: For a fixed repo snapshot + config, output diffs are constrained to expected nondeterministic fields only (e.g., timestamps), and core fields remain stable across reruns.
* Performance: ≥ 30% reduction in wall-clock time for typical runs via caching and concurrency.
* Quality: Measurable improvement on an evaluation set (e.g., fewer missing key concepts / higher rubric score) after optimizer compile.

Constraints, integrations, assumptions:

* DSPy should be upgraded to the actively released `dspy-ai` line; current release shows `dspy-ai 3.1.0` on Jan 6, 2026. ([PyPI][1])
* Structured outputs should be produced via DSPy adapters (JSON schema-backed for non-primitive fields) to ensure parseability. ([DSPy][2])
* Must support an event-driven/streaming agent loop with a deterministic “completion” signal (for chaining steps without polling), aligned with the project’s streaming-loop requirement.
* No timelines; delivery is phased by dependencies.

1. Capability Tree (Functional Decomposition)

Capability: DSPy Runtime Alignment
Description: Run lmstxt generator programs on DSPy 3.x with updated configuration and adapter patterns.
Feature: Package + API alignment (MVP)

* Description: Upgrade to `dspy-ai` and align configuration entrypoints.
* Inputs: Python environment, dependency constraints, runtime config.
* Outputs: Reproducible environment; runtime uses `dspy.configure`.
* Behavior: Pin/upgrade `dspy-ai`, replace deprecated config calls, ensure program runs end-to-end. ([PyPI][1])

Feature: LM configuration contexts (MVP)

* Description: Support global and scoped LM configuration for different stages (analysis vs generation).
* Inputs: LM identifiers, per-stage settings.
* Outputs: Correct LM routing per stage.
* Behavior: Use `dspy.configure` and scoped contexts where needed; keep thread-safe usage. ([DSPy][3])

Capability: Structured Repo Analysis Artifacts
Description: Produce deterministic, schema-validated repo analysis output for downstream automation.
Feature: Analysis schema definitions (MVP)

* Description: Define explicit schemas for repo purpose, key concepts, constraints, and “remember bullets”.
* Inputs: Repo snapshot metadata, extracted signals.
* Outputs: Typed artifact objects + serialized JSON.
* Behavior: Enforce required fields, constraints, versioning, and backward compatibility.

Feature: Adapter-driven structured outputs (MVP)

* Description: Use DSPy adapters to emit/parse structured outputs, including JSON schema for non-primitive fields.
* Inputs: Structured signature/types, repo context.
* Outputs: Parsed structured objects; validation results.
* Behavior: Generate with adapter formatting, parse into structured types, fail fast on schema violations. ([DSPy][2])

Feature: Validation + repair loop (MVP)

* Description: Detect schema violations and attempt bounded repair.
* Inputs: Raw model output, schema errors.
* Outputs: Valid artifact or explicit failure report.
* Behavior: Retry with targeted instructions; stop after N attempts; emit trace. (DSPy supports retry/error-handling patterns.) ([DSPy][4])

Capability: Performance and Cost Controls
Description: Reduce repeated work and improve throughput.
Feature: Deterministic caching (MVP)

* Description: Cache model calls and intermediate artifacts keyed by inputs/config.
* Inputs: Normalized request payloads, cache policy.
* Outputs: Cache hits/misses; reused responses.
* Behavior: Use DSPy cache mechanisms; allow custom storage backends and invalidation. ([DSPy][5])

Feature: Async/concurrent execution (Post-MVP)

* Description: Parallelize independent steps (e.g., file summarizations) safely.
* Inputs: Work items, concurrency limits.
* Outputs: Faster completion; bounded resource usage.
* Behavior: Execute tasks concurrently with stable ordering for final artifact assembly.

Capability: Quality Optimization and Evaluation
Description: Systematically improve prompts/programs against measurable metrics.
Feature: Evaluation harness (Post-MVP, prerequisite for optimization)

* Description: Define datasets + metrics for repo analysis quality.
* Inputs: Labeled/curated repos, expected fields, rubrics.
* Outputs: Scores, regressions, reports.
* Behavior: Run programs on eval set; record metrics; gate releases.

Feature: Optimizer compile with MIPROv2 (Post-MVP)

* Description: Use DSPy Optimizers (formerly teleprompters) to optimize instructions + few-shots jointly.
* Inputs: Program, metric, train/dev split.
* Outputs: Compiled program configuration (instructions/demos).
* Behavior: Run MIPROv2 compile; persist artifacts; compare to baseline. ([DSPy][6])

Capability: Streaming + Deterministic Completion Signaling
Description: Support streaming outputs while providing a deterministic end-of-stream signal to drive observe–decide–act loops.
Feature: Stream listener + completion event (MVP)

* Description: Emit incremental tokens/partial artifacts and a deterministic “done” event.
* Inputs: Streaming callbacks, step identifiers.
* Outputs: Stream events; final completion event with checksum/summary.
* Behavior: Collect stream deltas; finalize with a single authoritative completion event; downstream steps trigger only on completion.

1. Repository Structure + Module Definitions (Structural Decomposition)

Proposed structure (Python example; adjust to your repo conventions):

project-root/

* src/

  * config/

    * loader.py
    * schema.py
    * **init**.py
  * core_types/

    * analysis_artifacts.py
    * events.py
    * **init**.py
  * dspy_runtime/

    * runtime.py
    * adapters.py
    * cache.py
    * **init**.py
  * analysis_program/

    * signatures.py
    * program.py
    * validator.py
    * **init**.py
  * optimization/

    * datasets.py
    * metrics.py
    * compile.py
    * **init**.py
  * orchestration/

    * pipeline.py
    * streaming.py
    * **init**.py
  * io/

    * repo_reader.py
    * artifact_writer.py
    * **init**.py
* tests/

  * unit/
  * integration/
  * e2e/

Module: config

* Responsibility: Load and validate runtime configuration (LMs, caching, concurrency, schema versions).
* Exports: `load_config()`, `Config`

Module: core_types

* Responsibility: Canonical typed models (analysis artifacts, events, errors).
* Exports: `RepoAnalysisArtifact`, `StreamEvent`, `CompletionEvent`

Module: dspy_runtime

* Responsibility: DSPy initialization, adapter selection, caching integration, LM contexts.
* Exports: `configure_dspy(config)`, `get_adapter()`, `cache_get/cache_put`

Module: analysis_program

* Responsibility: DSPy signatures and program for repo analysis + validation/repair.
* Exports: `run_repo_analysis(repo_ctx) -> RepoAnalysisArtifact`, `validate_artifact()`

Module: optimization

* Responsibility: Eval datasets/metrics and optimizer compile flows (MIPROv2).
* Exports: `run_eval()`, `compile_program()`

Module: orchestration

* Responsibility: End-to-end pipeline, event-driven streaming, deterministic completion signaling.
* Exports: `run_pipeline()`, `stream_run_pipeline()`

Module: io

* Responsibility: Read repo snapshots and write output artifacts deterministically.
* Exports: `read_repo_context()`, `write_artifact()`

1. Dependency Chain (layers, explicit “Depends on: […]”)

Foundation layer (no dependencies):

* config: no dependencies
* core_types: no dependencies

Runtime layer:

* dspy_runtime: Depends on: [config, core_types]
* io: Depends on: [config, core_types]

Program layer:

* analysis_program: Depends on: [dspy_runtime, io, core_types]

Orchestration layer:

* orchestration: Depends on: [analysis_program, dspy_runtime, core_types]

Optimization layer (can be added after stable artifacts exist):

* optimization: Depends on: [analysis_program, dspy_runtime, core_types, io]

1. Development Phases (Phase 0…N; entry/exit criteria; tasks with dependencies + acceptance criteria + test strategy)

Phase 0: Foundation
Entry criteria: Repository builds/tests run; baseline pipeline exists.
Tasks:

* Implement config module (depends on: none)

  * Acceptance: Valid config loads; invalid config yields actionable errors.
  * Test: Unit tests for schema validation and defaults.
* Implement core_types models (depends on: none)

  * Acceptance: Models serialize/deserialize with version field; backward-compat paths defined.
  * Test: Unit tests for schema round-trip.

Exit criteria: Other modules can import config/core_types; no circular imports.

Phase 1: DSPy 3.x runtime alignment + structured artifacts (MVP path)
Entry criteria: Phase 0 complete.
Tasks:

* Upgrade to `dspy-ai` and align runtime configuration (depends on: [config])

  * Acceptance: Uses `dspy-ai` package; runtime uses `dspy.configure` for LM setup. ([PyPI][1])
  * Test: Integration test that initializes DSPy and runs a trivial signature.
* Add adapter-based structured output parsing (depends on: [dspy_runtime, core_types])

  * Acceptance: Analysis output parses into typed artifact; non-primitive fields use JSON schema-backed formatting. ([DSPy][2])
  * Test: Unit tests with mocked LM outputs; property tests for parser robustness.
* Implement analysis_program with validation + bounded repair (depends on: [dspy_runtime, io, core_types])

  * Acceptance: Produces schema-valid artifact or a failure report after N attempts; emits trace.
  * Test: Integration tests on small fixture repos; negative tests for malformed outputs.

Exit criteria: End-to-end run produces a deterministic, schema-valid JSON artifact for fixture repos.

Phase 2: Performance controls (MVP extension)
Entry criteria: Phase 1 complete; artifacts stable.
Tasks:

* Add deterministic caching (depends on: [dspy_runtime, config])

  * Acceptance: Repeat runs hit cache; configurable invalidation; cache key includes config+repo hash. ([DSPy][5])
  * Test: Integration test verifying cache hit behavior; unit tests for key stability.
* Add streaming events + deterministic completion event (depends on: [orchestration, core_types])

  * Acceptance: Streaming mode emits incremental events and exactly one completion event that gates downstream steps.
  * Test: E2E test validating event order, completion signal, and artifact checksum.

Exit criteria: Repeat runs are faster; streaming mode supports reliable chaining.

Phase 3: Evaluation + optimizer compile (Post-MVP)
Entry criteria: Stable artifacts; at least a small labeled eval set exists.
Tasks:

* Build evaluation harness (depends on: [analysis_program, io])

  * Acceptance: Runs eval set; outputs metric report; supports regression comparison.
  * Test: Golden tests for metric calculations; integration tests on fixed fixtures.
* Add MIPROv2 compile flow (depends on: [evaluation harness])

  * Acceptance: Can compile program and persist compiled configuration; shows improvement vs baseline on dev set. ([DSPy][6])
  * Test: Integration test that compiles on tiny dataset; deterministic seed where applicable.

Exit criteria: Repeatable compile + measurable quality improvements.

1. User Experience

Personas:

* Repo maintainer: Wants one command that produces stable JSON artifacts consumable by PRD/task tools.
* Tooling engineer: Wants schema guarantees, versioning, caching, and a streaming interface for agent loops.

Key flows:

* Batch mode: user points to repo → tool reads context → runs analysis → writes versioned JSON artifact + human-readable summary.
* Streaming mode: user runs pipeline with stream enabled → receives incremental events → receives deterministic completion → downstream step triggers automatically.
* Optimization mode (post-MVP): user runs eval → reviews report → runs compile → pins compiled config.

UI/UX notes:

* CLI should surface: schema version, validation status, cache hit/miss, and explicit completion reason.
* Failure should be actionable: include which field failed validation and whether repair attempts were exhausted.

1. Technical Architecture

System components:

* Repo context extractor (IO): collects file lists, metadata, selected content.
* DSPy runtime: configures LM, adapters, and caching.
* Analysis program: DSPy signatures + module pipeline producing typed artifacts.
* Orchestrator: runs pipeline; emits events; writes artifacts.
* Eval/optimizer (post-MVP): datasets, metrics, compile artifacts.

Data models:

* RepoContext: repo hash, file index, selected excerpts.
* RepoAnalysisArtifact (versioned): purpose, key concepts, constraints, interfaces, “remember bullets”, provenance.
* StreamEvent/CompletionEvent: step id, payload, monotonic sequence, final checksum.

Key decisions:

* Use `dspy-ai` 3.x as the runtime baseline to access current APIs and production-facing changes. ([PyPI][1])
* Prefer adapter-backed structured outputs to reduce brittleness and enable strict parsing. ([DSPy][2])
* Treat optimization as a separate layer gated on having an eval harness; use DSPy Optimizers and MIPROv2 when available. ([DSPy][6])

1. Test Strategy

Test pyramid targets:

* Unit: ~70% (schemas, parsing, cache keys, event sequencing logic)
* Integration: ~25% (DSPy runtime + analysis on fixture repos)
* E2E: ~5% (CLI runs, streaming completion gating, artifact diffs)

Coverage minimums:

* Line: 85%+
* Branch: 75%+
* Critical modules (analysis_program, orchestration): 90%+ line coverage

Critical scenarios by module:

* analysis_program

  * Happy: valid structured artifact produced.
  * Edge: empty repo / large repo / binary-heavy repo.
  * Error: model returns invalid JSON/schema; repair loop succeeds/fails deterministically.
* dspy_runtime.cache

  * Happy: stable key; correct hit/miss semantics.
  * Error: cache backend unavailable → graceful degradation with warnings.
* orchestration.streaming

  * Happy: ordered events; exactly one completion event; downstream triggers only on completion.
  * Error: stream interrupted → emits terminal failure completion event with reason.

Integration points:

* Adapter parsing + schema validation boundary.
* Cache key includes repo hash + config + signature version.

1. Risks and Mitigations

Risk: DSPy 3.x API surface changes cause integration churn.

* Impact: Medium
* Likelihood: Medium
* Mitigation: Isolate DSPy usage in `dspy_runtime`; pin versions; add contract tests around runtime initialization. ([PyPI][1])
* Fallback: Support a compatibility shim for older DSPy until migration completes.

Risk: Verbose JSON schema in prompts degrades output quality for nested types.

* Impact: Medium
* Likelihood: Medium
* Mitigation: Keep schemas shallow for MVP; introduce custom adapter formatting only if needed; add eval coverage focused on nested types. ([DSPy][2])
* Fallback: Use simpler field types and move nested structures to post-processing.

Risk: Caching introduces correctness bugs (stale outputs).

* Impact: High
* Likelihood: Medium
* Mitigation: Strong cache key design (repo hash + config + schema version); explicit invalidation controls; cache observability. ([DSPy][5])
* Fallback: Disable cache by default in suspicious environments; keep read-through optional.

Risk: Optimizer compile overfits small eval sets.

* Impact: Medium
* Likelihood: Medium
* Mitigation: Separate train/dev; track regressions; require improvement across multiple repos before adopting compiled config. ([DSPy][6])
* Fallback: Keep baseline program as default; allow opt-in compiled profile.

1. Appendix

A. Source notes

* Your current “core primitives only” framing and the recommended upgrade path are captured in your update notes.
* DSPy is actively released as `dspy-ai`, with `3.1.0` released Jan 6, 2026. ([PyPI][1])
* DSPy uses `dspy.configure` for LM configuration and supports thread-safe context usage. ([DSPy][3])
* Adapters support structured outputs and include JSON schema for non-primitive fields. ([DSPy][2])
* Optimizers (formerly teleprompters) and MIPROv2 are first-class for instruction + few-shot optimization. ([DSPy][6])
* DSPy cache customization is documented. ([DSPy][5])

B. Open questions (to resolve during implementation)

* What is the canonical schema for your repo analysis artifact (required fields, versioning policy)?
* What repos form the initial eval set, and what metric/rubric defines “better” output?
* What are the streaming event consumers, and what exact completion contract do they require (checksum fields, error payload shape)?
* What cache backend(s) are acceptable (disk, sqlite, redis), and what invalidation guarantees are required?

[1]: https://pypi.org/project/dspy-ai/?utm_source=chatgpt.com "dspy-ai"
[2]: https://dspy.ai/learn/programming/adapters/?utm_source=chatgpt.com "Adapters"
[3]: https://dspy.ai/learn/programming/language_models/?utm_source=chatgpt.com "Language Models"
[4]: https://dspy.ai/cheatsheet/?utm_source=chatgpt.com "DSPy Cheatsheet"
[5]: https://dspy.ai/tutorials/cache/?utm_source=chatgpt.com "Cache"
[6]: https://dspy.ai/learn/optimization/optimizers/?utm_source=chatgpt.com "Optimizers"
