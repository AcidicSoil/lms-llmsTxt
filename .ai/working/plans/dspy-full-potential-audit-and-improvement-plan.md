---
title: "DSPy Full-Potential Audit and Improvement Plan"
status: "draft"
owner: "lms-llmsTxt"
created_from_task: "Audit where the app underuses DSPy and plan improvements."
---

# DSPy Full-Potential Audit and Improvement Plan

## Goal

Find places where `lms-llmsTxt` relies on fixed heuristics, regexes, hard-coded scoring, one-off HTTP LM calls, or deterministic fallbacks where a bounded DSPy module, optimizer, evaluator, retriever, assertion, adapter, or observability integration would produce better repository understanding without weakening artifact contracts.

## Skill coverage matrix

This plan was built from the available local DSPy/AI/pattern skill families:

- **Core DSPy modeling:** signatures, modules, Predict, ChainOfThought, custom modules, primitives, adapters, LM configuration.
- **Reasoning/program design:** advanced module composition, two-step adapters, Program-of-Thought, ReAct/tool use, CodeAct, multi-chain comparison, ensemble, better-together.
- **Retrieval and grounding:** retrieval, RAG pipeline, Qdrant, Haystack integration, Ragas, citation/grounding patterns.
- **Quality controls:** assertions, output refinement constraints, Refine, best-of-N, labeled/few-shot/knn bootstrapping.
- **Optimization:** BootstrapFewShot, BootstrapRS, MIPROv2, COPRO, SIMBA, GEPA, optimize-anything, finetune/bootstrap variants.
- **Evaluation:** Evaluate, evaluation suite, LLM judge, AI scoring, AI testing safety, anomaly detection.
- **Runtime and scale:** async, parallel, streaming, data generation, cost cutting, switching models, vLLM/Ollama/RLM integration.
- **Observability:** MLflow, Phoenix, Langfuse, Langwatch, Langtrace, Weave, tracing requests.
- **Application patterns:** AI pipelines, chatbots, taking actions/tools, following rules, stopping hallucinations, searching docs, summarization, decomposing tasks.

## Current DSPy usage map

### Already using DSPy well enough to preserve

- `src/lms_llmsTxt/signatures.py`
  - Defines `AnalyzeRepository`, `AnalyzeCodeStructure`, `GenerateUsageExamples`, `PlanLLMsSections`, `SynthesizeLLMsSectionNotes`, `AnalyzeRepositoryFromDigest`, and `SynthesizeRepoGraphNodes`.
- `src/lms_llmsTxt/analyzer.py`
  - `RepositoryAnalyzer(dspy.Module)` composes repository analysis, structure analysis, examples, section planning, and section notes.
  - Uses deterministic rendering after model-assisted planning, which is good for artifact stability.
- `src/lms_llmsTxt/graph_dspy_synthesizer.py`
  - Uses per-node `ChainOfThought` graph synthesis for node-specific content.
- `src/lms_llmsTxt/lmstudio.py`
  - Custom `LMStudioJSONAdapter` bridges DSPy structured outputs to LM Studio JSON Schema mode.
- `src/lms_llmsTxt/evaluation.py`
  - Has deterministic evaluation primitives that can become DSPy optimizer metrics.

### Main underuse patterns

1. Heuristic selection and scoring are doing semantic work that should become DSPy-classified, then bounded by deterministic guards.
2. Digest construction summarizes files with string truncation and regex symbol/dependency extraction instead of typed extraction modules.
3. Evidence planning ranks paths with hard-coded weights instead of learned or judge-assisted relevance.
4. Graph relation scoring is static path/symbol overlap rather than relation inference.
5. Evaluation exists but is not wired into DSPy optimizers, best-of-N, regression gates, or prompt/module compilation.
6. Observability is mostly custom JSONL/logging, not DSPy trace-aware telemetry.
7. Some LM behavior bypasses DSPy through direct HTTP calls, which creates duplicated parsing, validation, and streaming logic.

## Opportunity backlog

### 1. Replace repo digest regex extraction with typed DSPy capsules

**Current hotspot**

- `src/lms_llmsTxt/repo_digest.py`
  - `_summarize()` truncates text.
  - `_extract_symbols()` uses regex.
  - `_extract_dependencies()` uses regex.
  - `extract_chunk_capsules()` builds capsules deterministically.

**DSPy improvement**

Add a `ExtractRepoChunkCapsule(dspy.Signature)` that outputs:

- `summary: str`
- `symbols: list[str]`
- `dependencies: list[str]`
- `domain_terms: list[str]`
- `role: Literal["entrypoint", "domain", "adapter", "config", "test", "docs", "generated", "asset"]`
- `confidence: float`

Wrap it in a `RepoChunkCapsuleExtractor(dspy.Module)` with deterministic fallback to current regex extraction.

Implementation note: keep the existing `ChunkCapsule` contract stable for `reduce_capsules()` initially. Store `domain_terms`, `role`, and `confidence` in an extended internal capsule/metadata sidecar, or explicitly extend `ChunkCapsule` and update all consumers in the same ticket.

**Why**

This is the highest-value upgrade because every later step depends on the digest. Regex extraction misses TypeScript exports, Rust modules, nested workspaces, framework conventions, and domain meaning.

**Skill alignment**

DSPy signatures, Predict, typed outputs, assertions, output refinement constraints, AI summarizing, AI searching docs.

**Validation**

- Keep existing `RepoDigest` schema unchanged.
- Add fixture repos with Python, TypeScript, Rust, and docs.
- Metric: capsule symbol/dependency/domain recall improves without increasing fallback rate.

---

### 2. Convert evidence path ranking into a DSPy reranker

**Current hotspot**

- `src/lms_llmsTxt/repo_digest.py`
  - `_path_priority()` uses hard-coded weights.
  - `plan_evidence_paths()` selects top paths by score.
- `src/lms_llmsTxt/rlm_evaluation.py`
  - `_candidate_priority()` repeats similar heuristic priority logic.

**DSPy improvement**

Add `RankEvidenceCandidates(dspy.Signature)`:

Inputs:

- repo digest summary
- candidate paths with lightweight metadata
- current artifact goal: `llms.txt`, `llms-full.txt`, `repo.graph.json`, `graph-node`
- budget limits

Outputs:

- ordered candidate IDs
- reason per selected candidate
- coverage tags: docs, entrypoint, tests, config, nested workspace, API, integration, domain model

Use deterministic budget enforcement after DSPy ranking.

**Why**

The app currently guesses what files matter from names. A DSPy reranker can decide that `apps/toolkit-converter/src/source-adapters/claude-code/skills-parser.ts` is more important than another `index.ts`, while still keeping strict fetch limits.

**Skill alignment**

DSPy Predict, AI sorting, AI scoring, RAG retrieval, RLM exploration, cost-cutting.

**Validation**

- Compare selected paths against benchmark expected subsystems.
- Use `evaluation.py` as the metric source.
- Keep heuristic reranker as fallback.

---

### 3. Use DSPy to plan semantic `llms.txt` sections before taxonomy fallback

**Current hotspot**

- `src/lms_llmsTxt/analyzer.py`
  - `TAXONOMY` regex buckets paths into Docs, Tutorials, API, Concepts, Optional.
  - `_score()` ranks pages with fixed string hints.
  - `_short_note()` templates path-based notes.

**DSPy improvement**

Add `ClassifyLLMsEntry(dspy.Signature)` and `PlanLLMsEntryBuckets(dspy.Module)`:

- Classify candidate links into semantic sections.
- Generate a grounded one-line reason.
- Preserve deterministic URL validation and rendering.

Keep `TAXONOMY` as fallback, not the primary selector.

**Why**

Path names alone are weak for polyglot/nested repos. DSPy can distinguish API surface, adapter contracts, domain models, CLI usage, examples, and integration docs using path plus fetched excerpt.

**Skill alignment**

DSPy signatures, Predict, ChainOfThought only for ambiguous classification, output constraints, AI sorting, AI writing content.

**Validation**

- Existing analyzer tests should still pass.
- Add benchmark cases where API docs live under unusual names.
- Track section note source: `model`, `taxonomy-fallback`, `deterministic-fallback`.

---

### 4. Replace graph relation scoring with relation inference

**Current hotspot**

- `src/lms_llmsTxt/graph_builder.py`
  - `_subsystem_relation_score()` uses root/path token/symbol overlap.
  - `_related_edges()` chooses neighbors from static scores.

**DSPy improvement**

Add `InferSubsystemRelations(dspy.Signature)`:

Inputs:

- source subsystem capsule
- target subsystem capsule
- shared symbols/imports/path evidence
- source excerpts when available

Outputs:

- relation type: calls, configures, validates, adapts, tests, documents, emits, persists, orchestrates, shares-domain-model
- strength score
- one-sentence relation rationale

Use heuristic scoring to prune candidate pairs, then DSPy ranks the top pairs.

**Why**

A graph should explain why nodes relate, not just connect similar-looking paths. This is especially important for generated graph node content and UI exploration.

**Skill alignment**

ChainOfThought, multi-chain comparison, assertions, output refinement constraints, AI decomposing tasks, AI scoring.

**Validation**

- Node links should include relation metadata in `repo.graph.json` or a compatible sidecar.
- Existing `RepoSkillGraph` contract can remain unchanged initially by storing relation rationale in node content or tags.
- Add evaluator metric: relation explanation specificity.

---

### 5. Make graph node synthesis a real DSPy program, not a single predictor

**Current hotspot**

- `src/lms_llmsTxt/graph_dspy_synthesizer.py`
  - Per-node `ChainOfThought` is now used, but validation is still external and single-pass.

**DSPy improvement**

Create a composed module:

1. `InferNodeRole`
2. `InferNodeRelations`
3. `DraftNodeMarkdown`
4. `JudgeNodeSpecificity`
5. `RefineNodeMarkdown` if specificity fails

Use `dspy.Refine` or `dspy.BestOfN` for nodes that fail validation. Keep deterministic validators as the hard gate before replacing output, and express generic-heading/boilerplate penalties through a reward function or judge score. Do not use `dspy.Assert` or `dspy.Suggest`; they are not available in DSPy 3.x.

**Why**

The repeated-header problem shows that one-shot generation is fragile. A DSPy program can self-check before the app falls back.

**Skill alignment**

Modules, Refine, BestOfN, deterministic validators, reward functions, output constraints, LLM judge, stopping hallucinations.

**Validation**

- Validator rejects generic section headings.
- New judge metric rejects path inventory prose.
- Graph tests include repeated-pattern regression fixtures.

---

### 6. Use DSPy retrieval for large/polyglot repositories

**Current hotspot**

- `src/lms_llmsTxt/repo_digest.py`
  - Selected evidence is fetched by bounded path ranking.
- `src/lms_llmsTxt/context_budget.py`
  - Context budget trims file tree/readme/package blobs.

**DSPy improvement**

Introduce a retrieval abstraction with two phases:

1. deterministic candidate extraction from file tree and manifests
2. DSPy retrieval/reranking over capsules/excerpts

Potential backends:

- in-memory lexical retriever first
- optional Qdrant or Haystack later
- optional RAGAS evaluation for retrieval quality

Runtime invariants:

- stable candidate IDs and deterministic final ordering after parallel completion
- per-module timeout and global run timeout
- max concurrent LM calls and max total calls per artifact
- cache key includes repo digest ID, path, chunk range, artifact goal, model policy version, and signature version
- duplicate candidate/path fetches are coalesced
- timeout/failure falls back to deterministic ranking without partial malformed model output

**Why**

Large repos need retrieval over semantically indexed chunks, not bigger prompts. This avoids “go shallow” behavior while keeping budgets bounded.

**Skill alignment**

DSPy retrieval, RAG pipeline, Qdrant, Haystack, RAGAS, AI searching docs, AI summarizing.

**Validation**

- Benchmark nested monorepos where key modules are deep under `apps`, `packages`, `services`, `crates`, `tools`, and `plugins`.
- Metric: expected subsystem coverage and selected evidence diversity.

---

### 7. Turn deterministic evaluation into DSPy optimizer metrics

**Current hotspot**

- `src/lms_llmsTxt/evaluation.py`
  - Model-free metrics exist, but no DSPy optimizer compiles modules against them.

**DSPy improvement**

Create an `optimization/` or `experiments/` package with:

- benchmark datasets
- `dspy.Evaluate` runner
- metrics wrapping `evaluate_llms_document()`
- candidates for current analyzer, planned analyzer, graph synthesizer
- BootstrapFewShot/MIPROv2/SIMBA experiments

Start with offline optimization only. Do not change production prompts until a candidate beats baseline.

**Why**

DSPy’s main benefit is optimization from examples. The app currently uses signatures but does not close the evaluation/optimization loop.

**Skill alignment**

Evaluate, evaluation suite, BootstrapFewShot, MIPROv2, SIMBA, GEPA, COPRO, labeled few-shot, KNN few-shot.

**Validation**

- `uv run pytest tests/test_evaluation.py`
- Add command: `lmstxt-eval --benchmark benchmarks/*.json --candidate analyzer-v2`
- Require non-negative score delta before rollout.

---

### 8. Add DSPy observability adapters

**Current hotspot**

- `src/lms_llmsTxt/pipeline.py`
  - JSONL events and run logs exist.
- `src/lms_llmsTxt/lmstudio.py`
  - LM configuration is centralized.

**DSPy improvement**

Add optional trace integrations behind env flags, optional extras, and lazy imports:

- MLflow for experiment runs
- Phoenix for local traces
- Langfuse/Langwatch/Langtrace/Weave as optional adapters

Dependency contract:

- core package imports must not require observability packages
- expose backend dependencies through focused extras such as `observability-mlflow`, `observability-phoenix`, and `observability-langfuse`
- define a small internal `TraceSink` protocol before adding backend-specific adapters

Trace fields:

- signature name
- module name
- token estimates
- fallback reason
- validation failure reason
- selected evidence path IDs
- optimizer candidate version

**Why**

DSPy improvement work needs traceability. Today it is hard to answer whether a bad output came from retrieval, planning, generation, parsing, validation, or fallback.

**Skill alignment**

DSPy MLflow, Phoenix, Langfuse, Langwatch, Langtrace, Weave, AI tracing requests, AI tracking experiments.

**Validation**

- Trace disabled by default.
- Tests assert no import-time dependency on optional observability packages.
- Smoke test with one enabled backend.

---

### 9. Replace direct semantic graph HTTP synthesis or retire it

**Current hotspot**

- `src/lms_llmsTxt/graph_semantic_synthesizer.py`
  - Direct LM Studio HTTP calls, manual streaming parser, manual JSON parsing, separate validation.

**DSPy improvement**

Either:

1. port this to a DSPy module using the LM Studio adapter, or
2. retire it if `graph_dspy_synthesizer.py` covers the same need.

**Why**

Direct LM calls duplicate adapter, streaming, JSON parsing, and validation logic. This bypasses DSPy optimizer and trace tooling.

**Skill alignment**

DSPy adapters, streaming, modules, output constraints, assertions.

**Validation**

- No artifact contract changes.
- Tests cover both current graph paths until one is retired.

---

### 10. Add model routing and cost controls as explicit DSPy policy

**Current hotspot**

- `src/lms_llmsTxt/lmstudio.py`
  - `_model_rank()` uses hard-coded hints.
- `src/lms_llmsTxt/config.py`
  - Model/context/streaming settings are static.

**DSPy improvement**

Add a model policy layer:

- small model for classification/ranking
- stronger model for final synthesis
- skip LM calls when deterministic confidence is high
- parallelize independent node/entry classification with budget caps

**Why**

Using one configured model for everything is easy but inefficient. DSPy programs can route simple Predict tasks to cheaper/faster models while reserving heavier reasoning for graph nodes and summaries.

**Skill alignment**

AI switching models, AI cutting costs, vLLM, Ollama, async, parallel, streaming.

**Validation**

- Default behavior unchanged unless env flag enables model routing.
- Track cost proxies: call count, prompt chars, output chars, fallback rate, latency.

---

## Proposed implementation phases

### Phase 0: Baseline and audit harness

- Add a command or test helper to produce a DSPy usage report:
  - signatures used
  - modules called
  - deterministic fallbacks hit
  - heuristic selectors used
  - validation failures
- Build or update benchmark fixtures for:
  - simple Python repo
  - docs-heavy repo
  - polyglot monorepo
  - nested app/package workspace
  - CLI-heavy project
  - large repo with deep important files

Exit criteria:

- Current baseline scores are captured.
- No production behavior changes.

### Phase 1: Typed chunk capsules and evidence reranking

- Implement `ExtractRepoChunkCapsule` before productionizing `RankEvidenceCandidates`.
- Keep deterministic extraction/ranking as fallback.
- Add trace fields for DSPy-vs-heuristic selection decisions.
- If evidence reranking starts before typed capsules, treat it as a path-only baseline (`TICKET-DSPY-020a`) and require a follow-up (`TICKET-DSPY-020b`) that consumes typed capsule metadata before rollout.

Exit criteria:

- Expected subsystem and evidence coverage improves on nested/polyglot benchmarks.
- No increase in failed generation rate.

### Phase 2: DSPy section planning and graph relation inference

- Replace primary path of `build_dynamic_buckets()` with DSPy classification when evidence is available.
- Add `InferSubsystemRelations` for graph edge rationale.
- Keep regex taxonomy/path overlap scoring as fallback and pruning.

Exit criteria:

- `llms.txt` sections are less path-name dependent.
- Graph edges explain actual relationships, not just shared folder names.

### Phase 3: DSPy refinement and judge loop

- Add `JudgeNodeSpecificity` and `RefineNodeMarkdown`.
- Use best-of-N/refine only when validators fail.
- Add repeated-pattern and boilerplate validators to evaluation reports.

Exit criteria:

- Generic node content fallback rate drops.
- No repeated template headings in generated graph nodes.

### Phase 4: Optimization loop

- Create benchmark train/dev sets.
- Run BootstrapFewShot or MIPROv2 over section planning, evidence ranking, and graph node synthesis modules.
- Save optimizer artifacts separately from production code.

Exit criteria:

- Candidate optimizer output beats baseline on held-out eval cases.
- Rollout is feature-flagged.

### Phase 5: Observability and runtime scaling

- Add optional DSPy trace backends.
- Add async/parallel node enrichment under strict call and timeout limits.
- Add model routing policy for cheap classification vs expensive synthesis.

Exit criteria:

- Trace can explain each output’s module decisions.
- Large repo latency improves without quality regression.

## Risk controls

- All DSPy upgrades must preserve artifact schemas and filenames.
- Deterministic fallbacks stay in place for offline/no-model mode.
- New modules should be behind feature flags until benchmark scores prove value.
- Hard budgets remain deterministic: max candidates, max fetches, max chars, max nodes, max retries.
- Model-generated content must pass validators before replacing deterministic output.

## Immediate next tickets

Every ticket must include:

- RED: add or extend a focused test that fails against current behavior.
- Verify failure: run `uv run pytest <test-file>::<test-name>` and record the failing assertion.
- GREEN: implement the smallest feature-flagged change that passes the focused test.
- Regression: run the relevant existing test file and confirm default behavior remains unchanged when the feature flag is disabled.

1. **TICKET-DSPY-001: DSPy usage report and heuristic inventory**
   - Generate a local report of signatures, modules, and heuristic fallback calls for one run.
2. **TICKET-DSPY-010: Typed repo chunk capsule extractor**
   - Replace regex-only capsule extraction with optional DSPy extraction.
3. **TICKET-DSPY-020: Evidence candidate reranker**
   - Add DSPy reranker with deterministic fallback and budget enforcement.
4. **TICKET-DSPY-030: Section classifier for llms.txt entries**
   - Replace primary regex taxonomy with model-assisted classification.
5. **TICKET-DSPY-040: Graph relation inference**
   - Add relation type/rationale inference for graph links.
6. **TICKET-DSPY-050: Node refinement loop**
   - Add judge/refine loop for graph nodes that fail specificity checks.
7. **TICKET-DSPY-060: Optimizer harness**
   - Wire deterministic evaluation metrics into DSPy optimization experiments.
8. **TICKET-DSPY-070: Optional DSPy trace backend**
   - Add Phoenix/MLflow first, then evaluate other observability backends.

## Recommended first slice

Start with **TICKET-DSPY-001 + TICKET-DSPY-010**, then implement **TICKET-DSPY-020** once typed capsule metadata exists.

Reason: evidence selection is upstream of every quality issue, but the reranker should consume stronger capsule metadata rather than only path-name heuristics. If a path-only reranker is desired first, scope it explicitly as **TICKET-DSPY-020a** and require **TICKET-DSPY-020b** to consume typed capsules before rollout.
