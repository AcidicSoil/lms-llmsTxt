# 1) Overview

## Problem Statement
`lms-llmsTxt` currently risks unstable behavior when repository inputs are large and when model responses include reasoning-style output. The current pipeline can pass large `file_tree`, `readme_content`, and `package_files` blobs directly into DSPy generation and uses `dspy.ChainOfThought(...)` in `RepositoryAnalyzer`, which increases output variability and token usage. This creates failure modes including context-length errors, payload-limit errors, and non-final output contamination in generated artifacts.

The project also has an opportunity to improve comprehension of generated artifacts through repository knowledge graphs (using the existing `hypergraph/` app baseline), but there is no grounded, auditable graph pipeline for repo-specific understanding.

## Target Users
- CLI users generating `llms.txt` artifacts for public/private GitHub repositories.
- MCP users consuming artifacts via chunked read tools and run history.
- Maintainers/operators who need predictable output quality and reduced generation failures.
- Developers/researchers who want deeper visual understanding of repository structure and concepts.

## Why Existing Approach Fails
- No explicit token-budget enforcement in generation orchestration.
- No progressive compaction ladder before fallback.
- Reasoning/final output channels are not explicitly normalized before persistence.
- `llms-full` can be misused as a direct prompt source without a formal retrieval-first contract.
- Graph generation is not yet integrated with deterministic repo evidence extraction.

## Success Metrics
- `TODO: Define target failure-rate SLO for context/payload errors (e.g., <= X% of runs).`
- `TODO: Define latency budget by repo size tiers (small/medium/large).`
- Zero persisted reasoning wrappers (`<think>`, `<analysis>`, "Reasoning:") in `*-llms.txt` outputs.
- 100% of generation runs enforce budget checks before model invocation.
- 100% of context-limit related failures attempt progressive reduction before fallback.
- For graph mode, 100% of generated nodes include auditable evidence references.

# 2) Capability Tree (Functional Decomposition)

## Capability: Reasoning-Safe Output Normalization
Ensure downstream logic consumes canonical final output only.

### Feature: Response Channel Canonicalization (MVP: Yes)
- **Description**: Convert provider/model responses into a stable `{final_text, reasoning_text}` internal representation.
- **Inputs**: Raw model output payload, provider metadata, optional structured reasoning fields.
- **Outputs**: Canonical response object with required `final_text` and optional `reasoning_text`.
- **Behavior**: Map structured reasoning fields when available; preserve final output contract regardless of provider format.

### Feature: Inline Reasoning Sanitizer (MVP: Yes)
- **Description**: Strip or isolate inline reasoning wrappers before artifact persistence.
- **Inputs**: `final_text` candidate string.
- **Outputs**: Sanitized final artifact text, optional extracted reasoning metadata.
- **Behavior**: Remove `<think>...</think>`, `<analysis>...</analysis>`, and reasoning-prefixed sections while preserving valid markdown structure.

### Feature: Reasoning Policy by Model Profile (MVP: No)
- **Description**: Apply stricter output constraints to known reasoning-heavy models.
- **Inputs**: Model id/profile, runtime configuration.
- **Outputs**: Effective generation policy (prompt style, output tokens, sanitizer strictness).
- **Behavior**: Enforce smaller output ceilings and final-only prompting for configured profiles.

## Capability: Context Budgeting and Compaction
Bound prompt size and guarantee convergence before model calls.

### Feature: Preflight Context Budgeter (MVP: Yes)
- **Description**: Compute token budget with reserved output and headroom.
- **Inputs**: Repository material, model context limits, reserved output tokens, headroom ratio.
- **Outputs**: Budget report and approved/rejected prompt plan.
- **Behavior**: Estimate token usage per component; reject oversized plans and invoke compaction ladder.

### Feature: Compaction Ladder (MVP: Yes)
- **Description**: Reduce context in deterministic stages until within hard limits.
- **Inputs**: Over-budget repository material and budget report.
- **Outputs**: Compacted repository material.
- **Behavior**: Trim file tree, trim README, trim package files, summarize overflow, deterministic truncation fallback.

### Feature: Progressive Retry for Context Errors (MVP: Yes)
- **Description**: Retry with stricter budgets on context-length/413-type failures before fallback mode.
- **Inputs**: Exception classification, previous budget snapshot.
- **Outputs**: New run attempt with reduced budgets or fallback trigger.
- **Behavior**: Retry at configured reduction steps (for example 70% then 50%), then fail closed to fallback.

## Capability: LCM-Style Context Management
Support long-horizon usage without one-shot context stuffing.

### Feature: Immutable Session Store (MVP: No)
- **Description**: Persist prompts, tool outputs, and artifact references append-only.
- **Inputs**: Run events, user/tool/model payload references.
- **Outputs**: Append-only event log with stable ids.
- **Behavior**: Never rewrites prior events; records derived summaries as separate nodes.

### Feature: Summary DAG + Active Context Builder (MVP: No)
- **Description**: Build active context from pinned constraints, recent raw items, and summary nodes.
- **Inputs**: Session store events, budget constraints.
- **Outputs**: Active-context payload and summary node updates.
- **Behavior**: Enforce soft/hard thresholds and guaranteed shrink convergence.

### Feature: Operator Primitives (Map/Reduce) for Repo Analysis (MVP: Yes)
- **Description**: Process large repositories via chunk-level typed extraction and deterministic reduction.
- **Inputs**: Chunked repository docs/snippets, extraction rubric.
- **Outputs**: Typed capsules and deterministic repo digest.
- **Behavior**: Map over chunks with schema validation, then reduce to high-signal digest used by final formatter.

### Feature: RLM-Style Recursive Fallback Mode (MVP: No)
- **Description**: Enable bounded recursive tooling for complex semantic tasks that resist deterministic decomposition.
- **Inputs**: Metadata references, tool APIs (`peek`, `grep`, `read_chunk`, `subcall`), budget caps.
- **Outputs**: Final structured result plus recursion trace.
- **Behavior**: Enforce max depth/subcall budgets, batching, and hard stop conditions.

## Capability: Repository Knowledge Graph Generation
Produce auditable graph artifacts for deeper repo understanding.

### Feature: Repo Digest to Graph Node Synthesis (MVP: Yes)
- **Description**: Convert typed repo digest into `SkillGraph`-compatible semantic nodes.
- **Inputs**: Repo digest JSON, selected chunk summaries, graph constraints.
- **Outputs**: `repo.graph.json`, markdown node files, typed links.
- **Behavior**: Generate 12–30 nodes, single MOC node, grounded links with prose justification.

### Feature: Evidence-Backed Nodes (MVP: Yes)
- **Description**: Attach source evidence to every graph node.
- **Inputs**: Capsule provenance (`path`, `start_line`, `end_line`, artifact refs).
- **Outputs**: Node `evidence[]` and `artifacts[]` sections.
- **Behavior**: Enforce evidence presence at validation time; block publish if missing.

### Feature: Graph UI Integration (MVP: No)
- **Description**: Load graph outputs in the local `hypergraph/` UI for force-graph + markdown exploration.
- **Inputs**: `repo.graph.json`, force projection, markdown node files.
- **Outputs**: Interactive view with preview and evidence links.
- **Behavior**: Replace topic-scrape generation route with repository graph load route.

# 3) Repository Structure + Module Definitions (Structural Decomposition)

## Proposed Structure

```text
project-root/
├── src/
│   ├── lms_llmsTxt/
│   │   ├── pipeline.py                        # orchestrates generation flow
│   │   ├── analyzer.py                        # DSPy module wiring
│   │   ├── config.py                          # runtime config
│   │   ├── reasoning.py                       # NEW: canonicalization + sanitization
│   │   ├── context_budget.py                  # NEW: token budgeting + thresholds
│   │   ├── context_compaction.py              # NEW: compaction ladder
│   │   ├── retry_policy.py                    # NEW: progressive retry strategies
│   │   ├── repo_digest.py                     # NEW: typed map/reduce digest
│   │   ├── graph_builder.py                   # NEW: digest -> SkillGraph/evidence nodes
│   │   └── graph_models.py                    # NEW: graph/evidence dataclasses
│   ├── lms_llmsTxt_mcp/
│   │   ├── artifacts.py                       # chunked artifact access
│   │   ├── server.py                          # MCP tool/resource routes
│   │   ├── graph_resources.py                 # NEW: graph artifact resources
│   │   └── session_memory.py                  # NEW: optional LCM store/DAG utilities
├── hypergraph/                                # existing UI baseline
│   ├── app/api/generate/route.ts              # adapt to repo graph load endpoint
│   ├── lib/generator.ts                       # adapt for repo graph ingestion
│   └── types/graph.ts                         # canonical graph type contract
└── tests/
    ├── test_reasoning.py                      # NEW
    ├── test_context_budget.py                 # NEW
    ├── test_context_compaction.py             # NEW
    ├── test_retry_policy.py                   # NEW
    ├── test_repo_digest.py                    # NEW
    ├── test_graph_builder.py                  # NEW
    └── existing pipeline/mcp tests
```

## Module Definitions

### Module: `src/lms_llmsTxt/reasoning.py`
- **Maps to capability**: Reasoning-Safe Output Normalization
- **Responsibility**: Normalize model output channels and sanitize persisted final text.
- **Public exports**:
  - `canonicalize_response(raw_output, provider_hint) -> CanonicalResponse`
  - `sanitize_final_output(text, strict: bool = True) -> SanitizedOutput`

### Module: `src/lms_llmsTxt/context_budget.py`
- **Maps to capability**: Context Budgeting and Compaction
- **Responsibility**: Estimate prompt token usage and enforce budget contracts.
- **Public exports**:
  - `build_context_budget(config, material) -> ContextBudget`
  - `validate_budget(budget) -> BudgetDecision`

### Module: `src/lms_llmsTxt/context_compaction.py`
- **Maps to capability**: Context Budgeting and Compaction
- **Responsibility**: Deterministic compaction ladder for oversized input.
- **Public exports**:
  - `compact_material(material, budget) -> RepositoryMaterial`
  - `summarize_overflow(chunks, budget) -> str`

### Module: `src/lms_llmsTxt/retry_policy.py`
- **Maps to capability**: Context Budgeting and Compaction
- **Responsibility**: Error classification and progressive retry plan generation.
- **Public exports**:
  - `classify_generation_error(exc) -> ErrorClass`
  - `next_retry_budget(previous_budget, step) -> ContextBudget`

### Module: `src/lms_llmsTxt/repo_digest.py`
- **Maps to capability**: LCM-Style Context Management
- **Responsibility**: Generate typed capsules and deterministic reduced digest from repo chunks.
- **Public exports**:
  - `extract_chunk_capsules(chunks, rubric) -> list[ChunkCapsule]`
  - `reduce_capsules(capsules) -> RepoDigest`

### Module: `src/lms_llmsTxt/graph_models.py`
- **Maps to capability**: Repository Knowledge Graph Generation
- **Responsibility**: Define graph and evidence schemas.
- **Public exports**:
  - `GraphNodeEvidence`
  - `RepoGraphNode`
  - `RepoSkillGraph`

### Module: `src/lms_llmsTxt/graph_builder.py`
- **Maps to capability**: Repository Knowledge Graph Generation
- **Responsibility**: Build grounded graph artifacts from repo digest.
- **Public exports**:
  - `build_repo_graph(digest, options) -> RepoSkillGraph`
  - `emit_graph_files(graph, output_dir) -> list[Path]`

### Module: `src/lms_llmsTxt/pipeline.py` (existing, enhanced)
- **Maps to capability**: Orchestration across all MVP features
- **Responsibility**: Orchestrate budget check, compaction, generation, sanitization, retries, fallback, and artifact writing.
- **Public exports**:
  - `prepare_repository_material(config, repo_url) -> RepositoryMaterial`
  - `run_generation(...) -> GenerationArtifacts`

### Module: `src/lms_llmsTxt/analyzer.py` (existing, enhanced)
- **Maps to capability**: Reasoning and repo digest generation inputs
- **Responsibility**: DSPy analysis/format generation with production-safe predictor mode.
- **Public exports**:
  - `RepositoryAnalyzer.forward(...) -> dspy.Prediction`
  - `build_dynamic_buckets(...) -> list[...]`

### Module: `src/lms_llmsTxt_mcp/graph_resources.py`
- **Maps to capability**: Repository Knowledge Graph Generation
- **Responsibility**: Expose graph outputs as MCP resources/tools with chunked reads.
- **Public exports**:
  - `graph_resource_uri(...) -> str`
  - `read_graph_artifact_chunk(...) -> str`

### Module: `src/lms_llmsTxt_mcp/session_memory.py` (optional non-MVP)
- **Maps to capability**: LCM-Style Context Management
- **Responsibility**: Immutable store + summary DAG utilities for multi-turn workflows.
- **Public exports**:
  - `append_event(...) -> EventId`
  - `build_active_context(...) -> ActiveContext`

### Module: `hypergraph/app/api/generate/route.ts` (existing, enhanced)
- **Maps to capability**: Graph UI Integration
- **Responsibility**: Serve repo graph loading endpoint instead of topic scrape-only generation.
- **Public exports**:
  - `POST /api/generate` (or renamed `POST /api/repo-graph`) route handler

# 4) Dependency Chain (layers, explicit “Depends on: [...]”)

## Foundation Layer (Phase 0)
No dependencies.

- **`src/lms_llmsTxt/graph_models.py`**: canonical graph/evidence schemas. Depends on: `[]`
- **`src/lms_llmsTxt/reasoning.py`**: canonicalization/sanitization primitives. Depends on: `[]`
- **`src/lms_llmsTxt/context_budget.py`**: budget datatypes + estimators. Depends on: `[]`
- **`src/lms_llmsTxt/retry_policy.py`**: error classification and retry-step policy. Depends on: `[]`

## Input Reduction Layer (Phase 1)

- **`src/lms_llmsTxt/context_compaction.py`**: deterministic context reduction. Depends on: `[src/lms_llmsTxt/context_budget.py]`
- **`src/lms_llmsTxt/repo_digest.py`**: typed map/reduce digest generation. Depends on: `[src/lms_llmsTxt/context_budget.py, src/lms_llmsTxt/context_compaction.py]`

## Generation Safety Layer (Phase 2)

- **`src/lms_llmsTxt/analyzer.py`** (enhancements): production-safe prediction mode and digest-aware input shaping. Depends on: `[src/lms_llmsTxt/repo_digest.py]`
- **`src/lms_llmsTxt/pipeline.py`** (enhancements): budget preflight, progressive retries, final sanitization. Depends on: `[src/lms_llmsTxt/reasoning.py, src/lms_llmsTxt/context_budget.py, src/lms_llmsTxt/context_compaction.py, src/lms_llmsTxt/retry_policy.py, src/lms_llmsTxt/analyzer.py]`

## Graph Construction Layer (Phase 3)

- **`src/lms_llmsTxt/graph_builder.py`**: digest -> grounded graph artifacts. Depends on: `[src/lms_llmsTxt/repo_digest.py, src/lms_llmsTxt/graph_models.py, src/lms_llmsTxt/reasoning.py]`
- **`src/lms_llmsTxt_mcp/graph_resources.py`**: graph artifact exposure and chunking. Depends on: `[src/lms_llmsTxt/graph_builder.py]`

## Experience Layer (Phase 4)

- **`hypergraph/app/api/generate/route.ts`** (adapted): repo graph load endpoint. Depends on: `[src/lms_llmsTxt/graph_builder.py]`
- **`hypergraph/lib/generator.ts`** (adapted or replaced): ingestion of prebuilt repo graph artifacts and optional validation. Depends on: `[hypergraph/types/graph.ts, src/lms_llmsTxt/graph_builder.py]`
- **`src/lms_llmsTxt_mcp/session_memory.py`** (optional): LCM immutable store and summary DAG. Depends on: `[src/lms_llmsTxt/context_budget.py, src/lms_llmsTxt/repo_digest.py]`

### Heavy Dependency Justifications
- `pipeline.py` depends on multiple modules because it is the single orchestration boundary; business logic remains in leaf modules.
- `graph_builder.py` depends on both digest and reasoning modules to enforce grounding and sanitize markdown node content.

# 5) Development Phases (Phase 0…N; entry/exit criteria; tasks with dependencies + acceptance criteria + test strategy)

## Phase 0: Foundations
### Entry Criteria
- Current tests pass on main branch.
- Agreement on naming/contracts for budget, reasoning, and graph schemas.

### Tasks
1. Implement `reasoning.py`, `context_budget.py`, `retry_policy.py`, `graph_models.py`.
   - **Dependencies**: none
   - **Acceptance criteria**:
     - Canonical response model supports `final_text` and optional `reasoning_text`.
     - Sanitizer removes known reasoning wrappers without breaking markdown headings/lists.
     - Budget model supports max context, reserved output, and headroom.
     - Retry policy classifies context-length and payload-limit error classes.
   - **Test strategy**:
     - Unit tests for sanitizer fixtures.
     - Unit tests for budget calculations and boundary conditions.
     - Unit tests for retry classification map.

### Exit Criteria
- New foundation unit tests green.
- No regressions in existing test suite.

## Phase 1: Context Reduction and Digest MVP
### Entry Criteria
- Phase 0 complete.

### Tasks
1. Implement `context_compaction.py` compaction ladder.
   - **Dependencies**: `context_budget.py`
   - **Acceptance criteria**:
     - Compaction steps execute deterministically in configured order.
     - At least one deterministic truncation path guarantees shrink under hard cap.
   - **Test strategy**:
     - Unit tests with oversized synthetic materials.

2. Implement `repo_digest.py` map/reduce typed capsules.
   - **Dependencies**: `context_budget.py`, `context_compaction.py`
   - **Acceptance criteria**:
     - Capsule schema validation blocks malformed map outputs.
     - Deterministic reducer produces stable digest for identical inputs.
   - **Test strategy**:
     - Snapshot tests for digest stability.
     - Property tests for reducer idempotence.

### Exit Criteria
- Digest generation works on at least one medium-size repository fixture.

## Phase 2: Safe Generation Path (MVP End-to-End Slice)
### Entry Criteria
- Phase 1 complete.

### Tasks
1. Enhance `analyzer.py` to use production-safe prediction path and digest-aware inputs.
   - **Dependencies**: `repo_digest.py`
   - **Acceptance criteria**:
     - Production mode no longer requires chain-of-thought output content.
     - Analyzer consumes compacted/digested inputs.
   - **Test strategy**:
     - Unit test with mocked DSPy calls; assert no reasoning-only contract reliance.

2. Enhance `pipeline.py` with preflight budget checks, progressive retries, and final sanitization.
   - **Dependencies**: `reasoning.py`, `context_budget.py`, `context_compaction.py`, `retry_policy.py`, enhanced `analyzer.py`
   - **Acceptance criteria**:
     - Every generation run performs budget preflight before model call.
     - Context/payload errors trigger retry budget reduction before fallback.
     - Persisted `llms.txt` has reasoning wrappers removed.
   - **Test strategy**:
     - Integration tests with synthetic over-limit input.
     - Retry-path tests via mocked exception classes.

### Exit Criteria
- MVP slice shipped: robust `llms.txt` generation with reduced context failure risk and sanitized outputs.

## Phase 3: Grounded Repo Knowledge Graph MVP
### Entry Criteria
- Phase 2 complete.

### Tasks
1. Implement `graph_builder.py` to create `repo.graph.json`, `repo.force.json`, and node markdown files.
   - **Dependencies**: `repo_digest.py`, `graph_models.py`, `reasoning.py`
   - **Acceptance criteria**:
     - Graph output enforces single MOC node.
     - Every node includes non-empty `evidence[]`.
     - Generated markdown includes meaningful links and valid ids.
   - **Test strategy**:
     - Schema validation tests.
     - Golden-file tests for graph artifact layout.

2. Implement MCP exposure for graph outputs (`graph_resources.py`).
   - **Dependencies**: `graph_builder.py`
   - **Acceptance criteria**:
     - Graph artifacts are discoverable via MCP resources.
     - Chunked reads behave consistently with existing artifact APIs.
   - **Test strategy**:
     - MCP tool/resource integration tests.

### Exit Criteria
- Graph artifacts are produced and consumable via CLI/MCP.

## Phase 4: UI Integration and Optional LCM Session Memory
### Entry Criteria
- Phase 3 complete.

### Tasks
1. Adapt `hypergraph` API/UI to load repo graph artifacts.
   - **Dependencies**: `graph_builder.py`
   - **Acceptance criteria**:
     - UI can render repo-generated graph and node markdown previews.
     - Evidence references are visible and clickable.
   - **Test strategy**:
     - Frontend integration test with fixture graph.

2. Add optional `session_memory.py` for LCM-like long-horizon workflows.
   - **Dependencies**: `context_budget.py`, `repo_digest.py`
   - **Acceptance criteria**:
     - Append-only event storage with stable ids.
     - Active context builder returns bounded context with summary nodes.
   - **Test strategy**:
     - Unit tests for append semantics and context assembly.

### Exit Criteria
- Visual repo understanding available in UI.
- Optional LCM memory path validated if enabled.

# 6) User Experience

## Personas
- **Artifact Producer**: runs `lmstxt` and expects reliable output across small/large repos.
- **MCP Consumer**: uses tools/resources to inspect artifacts incrementally without context blowups.
- **Repository Learner**: explores generated graph to understand repo architecture and pitfalls.

## Key Flows
1. User runs CLI on a repo URL.
2. System preflights budget, compacts inputs, generates `llms.txt`, and sanitizes output.
3. On context-related errors, system retries with stricter budgets before fallback.
4. User (optional) requests graph artifacts and opens them in the HyperGraph UI.
5. User explores MOC and linked nodes with evidence jumps to source snippets.

## UX Notes
- Keep failure messaging explicit: distinguish "retried with reduced context" from "fell back".
- Show budget diagnostics in verbose mode (estimated tokens, dropped sections, retry step).
- In graph UI, prioritize readability: MOC first, subsystem clustering, and evidence panel per node.

# 7) Technical Architecture

## Components
- **Collector**: existing GitHub material gathering (`gather_repository_material`).
- **Budget/Compaction Engine**: new budget calculator and deterministic reduction ladder.
- **Analysis Engine**: DSPy analyzer with production-safe output constraints.
- **Sanitization Layer**: final-output enforcement for artifact persistence.
- **Fallback Engine**: existing fallback payload/markdown generator, invoked after retry exhaustion.
- **Digest Engine**: typed map/reduce extraction from chunks.
- **Graph Engine**: digest-to-graph transformation with evidence.
- **MCP Exposure Layer**: run/resource APIs for text and graph artifacts.
- **UI Layer**: existing hypergraph app adapted for repo graph loading.

## Data Models
- `RepositoryMaterial` (existing): source repository inputs.
- `ContextBudget` (new): limits, estimates, headroom, decision state.
- `CanonicalResponse` (new): `final_text`, optional `reasoning_text`, metadata.
- `RepoDigest` (new): deterministic structural + semantic summary.
- `RepoSkillGraph` (new): graph nodes/links plus evidence references.

## API/Integration Boundaries
- CLI entrypoint remains unchanged for MVP (`lmstxt ...`).
- MCP adds graph resources/tools but keeps existing artifact URI patterns.
- HyperGraph API route switches from scrape-generation to repo-graph load (or supports both modes).

## Architecture Decisions
- **Decision**: Treat reasoning as non-contractual metadata; only final channel is contract.
  - **Rationale**: Prevents provider/model differences from breaking downstream consumers.
  - **Trade-off**: Potential loss of debugging richness unless reasoning retained separately.
  - **Alternative**: Preserve reasoning inline and parse downstream; rejected due to fragility.

- **Decision**: Enforce deterministic budget+compaction before any model call.
  - **Rationale**: Eliminates avoidable context/payload failures and improves predictability.
  - **Trade-off**: Additional preprocessing complexity and potential information loss.
  - **Alternative**: Rely on fallback after failure; rejected because it increases noisy failures.

- **Decision**: Use LCM-style map/reduce primitives first, RLM recursion as bounded fallback.
  - **Rationale**: Deterministic operators reduce variance and token waste.
  - **Trade-off**: More orchestration code and schema management.
  - **Alternative**: Single-shot long prompt; rejected for scalability/reliability concerns.

# 8) Test Strategy

## Test Pyramid Targets
- Unit: 65–75% of new test cases.
- Integration: 20–30% (pipeline + MCP + graph generation path).
- End-to-end/smoke: 5–10% (CLI run and optional UI flow).

## Coverage Minimums
- `TODO: Confirm project-wide minimum coverage gate for CI (recommended >= 85% changed lines).`
- 100% of new safety-critical branches (error classification, retry escalation, hard-cap truncation) must be covered.

## Critical Scenarios
- Reasoning wrapper stripping does not alter valid non-reasoning markdown.
- Budget preflight fails closed when limits are unknown or exceeded.
- Progressive retries trigger on context-length/413 style failures and stop at configured floor.
- Fallback remains functional after retry exhaustion.
- Digest reducer output remains stable for deterministic inputs.
- Graph validation rejects nodes missing evidence.
- MCP chunk readers for graph artifacts handle bounds, missing files, and non-UTF-8 content safely.

## Integration Points
- `pipeline.py` + `analyzer.py` with mocked DSPy and LM Studio error classes.
- `graph_builder.py` + MCP resource layer.
- Optional UI route tests loading fixture graph JSON and markdown nodes.

# 9) Risks and Mitigations

## Technical Risks
- **Risk**: Token estimation mismatch across models causes under-budget failures.
  - **Impact**: High
  - **Likelihood**: Medium
  - **Mitigation**: Conservative headroom defaults; configurable estimator; progressive retries.
  - **Fallback**: Immediate deterministic truncation and heuristic fallback generation.

- **Risk**: Sanitizer removes legitimate content patterns.
  - **Impact**: Medium
  - **Likelihood**: Medium
  - **Mitigation**: Rule-scoped regexes, fixture-based tests, strict/lenient modes.
  - **Fallback**: Preserve original artifact in debug channel only.

- **Risk**: Digest map/reduce schema drift leads to brittle graph generation.
  - **Impact**: Medium
  - **Likelihood**: Medium
  - **Mitigation**: Versioned schemas and contract tests.
  - **Fallback**: Generate reduced graph from deterministic structure only.

## Dependency Risks
- **Risk**: DSPy behavior differences across versions affect predictor output shape.
  - **Impact**: Medium
  - **Likelihood**: Medium
  - **Mitigation**: Pin supported versions and add compatibility tests.
  - **Fallback**: Route to fallback payload path with warning.

- **Risk**: HyperGraph integration diverges from local schema contracts.
  - **Impact**: Medium
  - **Likelihood**: Low
  - **Mitigation**: Keep `types/graph.ts` as explicit schema boundary and validate input.
  - **Fallback**: Provide non-UI graph artifact consumption path via MCP/CLI.

## Scope Risks
- **Risk**: Trying to ship full LCM + RLM recursion in MVP delays core reliability fixes.
  - **Impact**: High
  - **Likelihood**: Medium
  - **Mitigation**: Keep MVP to budget/compaction/sanitization + digest + grounded graph core.
  - **Fallback**: Defer `session_memory.py` and recursive mode to post-MVP phase.

# 10) Appendix

## Source Inputs Used
- `Handling Reasoning in Models.md` (exported notes with recommendations on reasoning output handling, context management, LCM/RLM usage, and hypergraph integration).
- Existing project files:
  - `src/lms_llmsTxt/pipeline.py`
  - `src/lms_llmsTxt/analyzer.py`
  - `src/lms_llmsTxt/config.py`
  - `src/lms_llmsTxt_mcp/artifacts.py`
  - `hypergraph/lib/generator.ts`

## Glossary
- **LCM**: Layered/long-context memory pattern using immutable storage + summary DAG + bounded active context.
- **RLM**: Recursive long-context model pattern using tool-assisted recursive decomposition.
- **MOC**: Map of Content; primary graph entry node.
- **Repo Digest**: Typed, reduced, high-signal summary derived from chunk-level extraction.

## Open Questions
- `TODO: Which exact models/profiles are in production and require strict reasoning policy defaults?`
- `TODO: Should graph generation be gated behind a CLI flag (`--graph`) or separate command?`
- `TODO: Should graph artifacts be generated on every run or only on demand?`
- `TODO: What retention policy is required for optional session memory artifacts?`

# 11) Task-Master Integration notes

- **Capabilities -> tasks**:
  - Reasoning-Safe Output Normalization
  - Context Budgeting and Compaction
  - LCM-Style Context Management
  - Repository Knowledge Graph Generation
- **Features -> subtasks**:
  - Each feature listed under capability tree maps directly to a subtask.
- **Dependencies -> task deps**:
  - Use Section 4 module dependency list to define acyclic task dependencies.
- **Phases -> priorities**:
  - Phase 0/1/2 are MVP and should be prioritized before Phase 3/4 enhancements.
