**Ambiguity: 0.10**

# Parent Ticket

* **Title:** Snapshot review follow-ups for artifact security, graph credibility, analyzer architecture, and MCP throughput (Parent ticket)
* **Summary:**

  * The review describes one critical security defect, four implementation/design defects, and one graph-UX credibility defect.
  * The review also includes sequencing guidance on what to change first, plus notes about solid areas and stated assumptions.
  * Where the review offered mutually exclusive implementation directions, this split plan follows the higher-reward branch and preserves the unselected alternative in the relevant ticket.
  * Suggested CAR rendering: keep tickets in ascending `TICKET-###` order with explicit `Tasks`, `Acceptance criteria`, and `Tests`, per the uploaded ticket skill.  
* **Source:**

  * **Link/ID:** `.codefetch/artifacts/test-review-review.md`
  * **Original ticket excerpt:** “The snapshot has one real security bug and two credibility problems.”
* **Global Constraints:**

  * Code-snapshot review only.
  * Do not infer runtime behavior beyond what the code directly supports.
  * Preserve security/privacy concerns around artifact persistence.
  * Keep graph claims aligned with what the underlying extraction can justify.
* **Global Environment:**

  * Code snapshot only.
  * Runtime environment: Unknown.
  * Trust boundary for MCP callers: assumed untrusted or semi-trusted by the review; exact deployment context not provided.
* **Global Evidence:**

  * Snapshot references in review: `4227–4244`, `4015–4026`, `4605–4617`, `4686–4695`
  * Snapshot references in review: `3084–3110`, `3131–3178`, `1860–1922`
  * Snapshot references in review: `2798–2827`, `2976–2999`
  * Snapshot references in review: `343–354`, `428–457`
  * Snapshot references in review: `3575`, `3703–3758`, `3777–3856`, `3875–3942`, `947–949`, `2794–2796`
  * Snapshot references in review: `1880–1891`, `1894–1919`, `1925–1939`

# Split Plan

* **Coverage Map:**

  * Original item: “Graph read surface bypasses the only path guard”
    Assigned Ticket ID: **T1**
  * Original item: “Unify artifact-path resolution behind one canonical containment check and remove direct `root / relative_path` reads.”
    Assigned Ticket ID: **T1**
  * Original item: “The graph is metadata dressed up as evidence”
    Assigned Ticket ID: **T2**
  * Original item: “Ingest actual source content for a bounded set of important files”
    Assigned Ticket ID: **T2**
  * Original item: “Derive symbols, dependencies, and evidence from real text spans”
    Assigned Ticket ID: **T3**
  * Original item: “Stop emitting fake evidence”
    Assigned Ticket ID: **T3**
  * Original item: “`llms-ctx.txt` can leak unsanitized model output”
    Assigned Ticket ID: **T4**
  * Original item: “Sanitize once, derive everything from the sanitized payload”
    Assigned Ticket ID: **T4**
  * Original item: “The analyzer architecture is elaborate, but the output path is mostly heuristic”
    Assigned Ticket ID: **T5**
  * Original item: “Use the final-generation signature and make the output genuinely model-authored with deterministic post-validation”
    Assigned Ticket ID: **T5**
  * Original item: “Do not keep both architectures superimposed”
    Assigned Ticket ID: **T5**
  * Original item: “Throughput is artificially throttled by a global mutex plus default auto-unload”
    Assigned Ticket ID: **T6**
  * Original item: “Keep one concurrency limiter around LM Studio calls; allow non-LM work to proceed concurrently; keep model warm by default”
    Assigned Ticket ID: **T6**
  * Original item: “The graph topology is too shallow to support the UI claims”
    Assigned Ticket ID: **T7**
  * Original item: “Add real edges”
    Assigned Ticket ID: **T7**
  * Original item: “Close the graph path traversal hole”
    Assigned Ticket ID: **T1**
  * Original item: “Stop emitting fake evidence”
    Assigned Ticket ID: **T3**
  * Original item: “Fix `llms-ctx.txt` generation immediately”
    Assigned Ticket ID: **T4**
  * Original item: “Simplify the analyzer path”
    Assigned Ticket ID: **T5**
  * Original item: “Remove the whole-service mutex / warm the model by default in server mode”
    Assigned Ticket ID: **T6**
  * Original item: “The LM Studio connectivity layer is more defensive than the rest of the system”
    Assigned Ticket ID: **Info-only**
  * Original item: “The run store has sane basic hygiene”
    Assigned Ticket ID: **Info-only**
  * Original item: “The path-validation intent is correct; the problem is inconsistency”
    Assigned Ticket ID: **Info-only**
  * Original item: “Assuming the MCP graph read handlers are reachable by untrusted or semi-trusted callers”
    Assigned Ticket ID: **Info-only**
  * Original item: “I am not asserting that reasoning leakage has already happened in production”
    Assigned Ticket ID: **Info-only**
  * Original item: “I am inferring that the graph is meant to support repository understanding rather than merely decorate a UI”
    Assigned Ticket ID: **Info-only**

* **Dependencies:**

  * **T3 depends on T2** because span-backed evidence requires real source-backed repository material.
  * **T7 depends on T2** because real graph edges need stronger source-backed extraction than filename-only chunks.
  * **T7 depends on T3** because graph credibility improves only after evidence claims are grounded.

* **Split Tickets:**

## T1 Title: TICKET-010 Secure all artifact reads behind one canonical root-containment guard

* **Type:** bug
* **Target Area:** Graph artifact read surface, persistent artifact read surface, shared path-resolution utilities
* **Summary:**

  * The review identifies a direct trust-boundary failure in the graph artifact read path: safe path validation exists, but the public graph-read path bypasses it.
  * This ticket closes the path traversal/file disclosure risk by forcing all artifact reads through one canonical containment check.
  * The ticket also aligns behavior across graph artifacts and persistent artifacts so there is no separate “fast” unsafe path.
* **In Scope:**

  * Route graph artifact reads through the canonical validated path helper.
  * Remove direct `root / relative_path` read behavior from the exposed graph-read path.
  * Resolve symlinks and reject non-descendants of the allowed root.
  * Reject directories and non-UTF-8 content when appropriate.
  * Apply the same guard to graph artifacts, persistent artifacts, and equivalent future resource surfaces named by the review.
* **Out of Scope:**

  * Preserving accidental out-of-root reads relied on by existing callers.
  * Unrelated LM Studio, analyzer, or graph-topology work.
* **Current Behavior (Actual):**

  * `validate_output_dir()` performs containment checks.
  * `read_graph_artifact_chunk()` reads `root / relative_path` directly instead of using the guard.
  * Public MCP handlers expose that path to callers.
* **Expected Behavior:**

  * Every artifact read resolves through one canonical validated path helper.
  * Out-of-root traversal attempts are rejected.
  * Graph and persistent artifact surfaces enforce the same root-boundary rules.
* **Reproduction Steps:**

  1. Call the public graph artifact read surface with a relative path containing traversal segments.
  2. Observe that the request reaches the direct `root / relative_path` read path rather than the containment helper.
  3. Confirm the read path bypasses the root guard described in the review.
* **Requirements / Constraints:**

  * Join under the allowed root.
  * Resolve symlinks.
  * Reject non-descendants of the root.
  * Reject directories and non-UTF-8 when appropriate.
  * Do not keep separate safe and unsafe read paths.
* **Evidence:**

  * Snapshot lines: `4227–4244`, `4015–4026`, `4605–4617`, `4686–4695`
  * Review consequence: arbitrary file disclosure / weakened tenant isolation / potential credential or config leakage
* **Open Items / Unknowns:**

  * Exact caller trust model is not provided.
  * Exact set of all artifact/resource surfaces beyond those named in the review is not provided.
* **Risks / Dependencies:**

  * May break callers that were accidentally relying on out-of-root reads.
* **Acceptance Criteria:**

  * Graph artifact reads no longer bypass the root-containment validator.
  * A single canonical helper is used for graph artifacts and persistent artifacts.
  * Symlink traversal and `../`-style non-descendant reads are rejected.
  * Direct `root / relative_path` reads are removed from the exposed graph-read path.
  * Directory and invalid-text handling matches the review guidance.
* **Priority & Severity (if inferable from input text):**

  * **Priority:** P0
  * **Severity:** S0
* **Source:**

  * “Graph read surface bypasses the only path guard”
  * “`read_graph_artifact_chunk()` does not use it”
  * “one `../../` away from reading things you never meant to expose”

---

## T2 Title: TICKET-020 Ingest real source content for bounded high-value files in repository chunking

* **Type:** enhancement
* **Target Area:** Repository chunking, repo digest input material, subsystem analysis inputs
* **Summary:**

  * The review says most repo-graph analysis is being inferred from filenames because `RepoChunk` content is often just the path string.
  * This ticket upgrades repository chunking so the analysis pipeline ingests actual source text for a bounded set of important files instead of presenting path metadata as if it were source-backed analysis.
  * This is the high-reward branch explicitly offered by the review.
* **In Scope:**

  * Replace filename-only chunk content for a bounded set of important files with actual source content.
  * Preserve README/package ingestion already present.
  * Ensure subsystem analysis inputs are source-backed where the graph intends to infer repository behavior, symbols, or dependencies.
  * Keep the scope bounded to avoid unbounded file fetching/token cost, consistent with the review wording.
* **Out of Scope:**

  * The fallback “downgrade the graph to a path-topology map” path.
  * Real evidence-span emission itself.
  * Graph edge construction itself.
* **Current Behavior (Actual):**

  * `chunk_repository_material()` creates `RepoChunk` entries from file paths.
  * Most chunk content is `content=path`.
  * Only README/package blobs contain actual file content.
* **Expected Behavior:**

  * Repository analysis for important files is driven by actual source text rather than filenames.
  * Filename-only metadata is no longer the primary basis for subsystem summaries, dependencies, and symbols in the upgraded path.
* **Reproduction Steps:**

  1. Inspect `chunk_repository_material()` behavior for normal file-tree entries.
  2. Observe path-string chunk content for most files.
  3. Trace downstream extraction consuming those chunks as if they represented source-backed content.
* **Requirements / Constraints:**

  * Use actual source content for a bounded set of important files.
  * Keep the bounded-ingestion design explicit.
  * Align graph claims with what the ingestion layer can support.
* **Evidence:**

  * Snapshot lines: `3084–3110`, `3131–3178`
  * Review consequence: misleading onboarding, incorrect dependency assumptions, bogus entry points, wasted debugging time
* **Open Items / Unknowns:**

  * The exact definition of “important files” is not provided.
  * The exact bounding strategy for file fetching is not provided.
* **Risks / Dependencies:**

  * Higher I/O and token budget.
  * Depends on careful selective file-fetch logic.
* **Acceptance Criteria:**

  * Repository chunking ingests actual source content for a bounded set of important files.
  * Filename-only path strings are no longer used as the primary content source for source-backed subsystem analysis in that bounded set.
  * Downstream subsystem analysis consumes real text for the upgraded file set.
  * The ingestion scope remains explicitly bounded.
* **Priority & Severity (if inferable from input text):**

  * **Priority:** P1
  * **Severity:** S1
* **Source:**

  * “`content=path`; only README and package blobs contain actual file content”
  * “The graph is metadata dressed up as evidence”
  * “ingest actual source content for a bounded set of important files”

---

## T3 Title: TICKET-030 Replace fake evidence anchors with real span-backed evidence in the repo graph

* **Type:** enhancement
* **Target Area:** Graph evidence model, repo graph construction, MOC/user-facing graph claims
* **Summary:**

  * The review calls out evidence entries that all point to line 1 and a shared `repo_digest` artifact reference, which makes the graph look evidence-backed when it is not.
  * This ticket makes evidence honest by deriving evidence from real text spans and removing fake anchors from subsystem nodes.
  * It also aligns user-facing graph language with the actual evidence quality.
* **In Scope:**

  * Replace `start_line=1` / `end_line=1` placeholder evidence with evidence backed by real text spans.
  * Remove fake evidence anchors from subsystem nodes.
  * Align graph/MOC claims so they do not promise evidence-backed navigation unless supported by real evidence.
  * Ensure symbols and dependency semantics shown to users are backed by real extracted evidence.
* **Out of Scope:**

  * The fallback “remove claims and downgrade to path map” path.
  * Source-ingestion foundation work covered by T2.
  * Real graph-edge expansion covered by T7.
* **Current Behavior (Actual):**

  * `GraphNodeEvidence` entries are emitted with `start_line=1`, `end_line=1`, and `artifact_ref="repo_digest"` for subsystem paths.
  * The graph tells users to follow evidence-backed links even though the anchors are placeholders.
* **Expected Behavior:**

  * Evidence entries reference real extracted spans.
  * User-facing graph copy no longer overstates evidence quality.
  * Symbols/dependencies presented through the graph are supportable from actual extracted evidence.
* **Reproduction Steps:**

  1. Inspect graph node evidence emitted for subsystem paths.
  2. Observe line-1 placeholder anchors and shared `repo_digest` references.
  3. Compare those anchors with graph text that implies evidence-backed exploration.
* **Requirements / Constraints:**

  * Evidence must come from real text spans.
  * Do not present placeholder anchors as evidence.
  * Keep graph claims aligned with what the underlying evidence can justify.
* **Evidence:**

  * Snapshot lines: `1860–1922`
  * Review consequence: plausible-but-wrong graph, over-trust, wasted debugging time
* **Open Items / Unknowns:**

  * Exact evidence schema beyond the fields named in the review is not provided.
  * Exact user-facing copy locations outside `moc_content` are not provided.
* **Risks / Dependencies:**

  * Depends on T2 for source-backed extraction.
* **Acceptance Criteria:**

  * Subsystem graph nodes no longer emit line-1 placeholder evidence as if it were real support.
  * Evidence shown in the graph is backed by real extracted spans.
  * User-facing graph copy does not instruct users to follow evidence-backed links unless the evidence is real.
  * Symbols/dependencies exposed through this surface are grounded in actual extracted evidence.
* **Priority & Severity (if inferable from input text):**

  * **Priority:** P1
  * **Severity:** S1
* **Source:**

  * “`GraphNodeEvidence` entries with `start_line=1`, `end_line=1`”
  * “`artifact_ref="repo_digest"` for every subsystem path”
  * “derive symbols, dependencies, and evidence from real text spans”

---

## T4 Title: TICKET-040 Derive all persisted llms artifacts from one sanitized payload

* **Type:** bug
* **Target Area:** `run_generation()`, `llms.txt`, `llms-full.txt`, `llms-ctx.txt`, ctx generation
* **Summary:**

  * The review identifies an inconsistent privacy boundary: `llms.txt` and `llms-full.txt` use sanitized output, but `llms-ctx.txt` is derived from raw model output.
  * This ticket closes that leak path by sanitizing once and ensuring every persisted downstream artifact derives from the sanitized payload.
  * The change is localized and high-value.
* **In Scope:**

  * Use one canonical sanitized payload for downstream persisted artifacts.
  * Ensure `llms.txt`, `llms-full.txt`, and `llms-ctx.txt` all derive from sanitized text.
  * Prevent raw provider/private reasoning text from reaching persisted user-facing artifacts.
  * Preserve raw text only if a downstream step explicitly requires it and it is isolated from persistence, per the review.
* **Out of Scope:**

  * Broader analyzer architecture work.
  * Assertions about whether production leakage has already occurred.
* **Current Behavior (Actual):**

  * `llms.txt` uses `sanitize_final_output()`.
  * `llms-full.txt` uses sanitized text.
  * `llms-ctx.txt` is built from raw `llms_text` via `create_ctx(llms_text, optional=False)`.
* **Expected Behavior:**

  * All persisted llms artifacts derive from the same sanitized payload.
  * Provider-only reasoning blocks and reasoning-prefixed lines are stripped consistently.
* **Reproduction Steps:**

  1. Trace `run_generation()` artifact creation flow.
  2. Observe sanitized handling for `llms.txt` and `llms-full.txt`.
  3. Observe raw `llms_text` passed into `create_ctx(...)` for `llms-ctx.txt`.
* **Requirements / Constraints:**

  * Sanitize once.
  * Persist sanitized text.
  * Derive ctx/full from sanitized text.
  * Only keep raw text outside persistence if explicitly required and isolated.
* **Evidence:**

  * Snapshot lines: `2798–2827`, `2976–2999`
  * Review consequence: reasoning leakage / inconsistent artifacts / privacy-compliance footgun
* **Open Items / Unknowns:**

  * Any separate non-user artifact for raw extracted reasoning is not described.
* **Risks / Dependencies:**

  * Minimal implementation risk per the review.
* **Acceptance Criteria:**

  * `llms-ctx.txt` no longer derives from raw `llms_text`.
  * `llms.txt`, `llms-full.txt`, and `llms-ctx.txt` all derive from one sanitized payload.
  * Sanitization removes `<think>`, `<analysis>`, `<reasoning>` blocks and reasoning-prefixed lines consistently across persisted artifacts.
  * No persisted downstream artifact reopens the raw-output leak path described in the review.
* **Priority & Severity (if inferable from input text):**

  * **Priority:** P1
  * **Severity:** S1
* **Source:**

  * “`llms-ctx.txt` can leak unsanitized model output”
  * “`llms-ctx.txt` is built from raw `llms_text`”
  * “sanitize once, derive everything from the sanitized payload”

---

## T5 Title: TICKET-050 Collapse the analyzer onto a model-first final generation path

* **Type:** chore
* **Target Area:** `RepositoryAnalyzer`, DSPy predictor wiring, final llms artifact generation path
* **Summary:**

  * The review says the analyzer stack pays for DSPy complexity while the final output is still mostly heuristic markdown assembly, and some model-driven stages are unused.
  * This ticket resolves that mismatch by taking the model-first branch named in the review: make final output genuinely model-authored through the final-generation signature, with deterministic post-validation.
  * It also removes the superimposed architecture problem where model stages exist but are not meaningfully part of the output path.
* **In Scope:**

  * Wire final artifact generation through the final-generation signature already present in the analyzer stack.
  * Ensure `generate_examples(...)` and `generate_llms_txt` are either meaningfully consumed by the final path or removed from the active architecture if still unused.
  * Keep deterministic post-validation on the final model-authored output.
  * Eliminate the mixed state where the system carries both elaborate DSPy wiring and a mostly heuristic final assembly path.
* **Out of Scope:**

  * The alternative heuristic-first simplification path noted by the review.
  * LM Studio concurrency/model lifecycle work.
  * Graph evidence/topology work.
* **Current Behavior (Actual):**

  * `RepositoryAnalyzer.__init__()` wires multiple predictors.
  * `self.generate_examples(...)` is called and its result is ignored.
  * `self.generate_llms_txt` is configured but never used.
  * Final artifact is assembled by `render_llms_markdown()` from heuristic inputs.
* **Expected Behavior:**

  * Final llms output comes from the model-first generation path described by the review.
  * Dead or ignored stages are no longer left superimposed on the active architecture.
  * Deterministic post-validation constrains the model-authored output.
* **Reproduction Steps:**

  1. Inspect predictor wiring in `RepositoryAnalyzer.__init__()`.
  2. Trace `forward()` and observe ignored `generate_examples(...)` output.
  3. Observe heuristic markdown assembly as the actual final-output path.
* **Requirements / Constraints:**

  * Use the final-generation signature.
  * Make the output genuinely model-authored.
  * Apply deterministic post-validation.
  * Do not keep both architectures superimposed.
* **Evidence:**

  * Snapshot lines: `343–354`, `428–457`
  * Review consequence: higher latency, harder debugging, confused maintainers, false sense of model-driven behavior
* **Open Items / Unknowns:**

  * Exact post-validation rules are not specified in the review.
  * Exact fate of each DSPy signature beyond the named ones is not provided.
* **Risks / Dependencies:**

  * Architectural change across the analyzer path.
  * Possible behavior/output-format change relative to the current heuristic renderer.
* **Acceptance Criteria:**

  * The final llms artifact is generated through the model-first final-generation signature.
  * Deterministic post-validation is applied to the final generated output.
  * `generate_examples(...)` and `generate_llms_txt` are not left configured-and-ignored in the active path.
  * The analyzer no longer carries both a heavy DSPy surface and a separate heuristic final-output architecture as parallel truths.
* **Priority & Severity (if inferable from input text):**

  * **Priority:** P1
  * **Severity:** S1
* **Source:**

  * “The analyzer architecture is elaborate, but the output path is mostly heuristic”
  * “`self.generate_examples(...)` is called and its result is ignored”
  * “Do not keep both architectures superimposed”

---

## T6 Title: TICKET-060 Remove whole-service serialization and keep the model warm in server mode

* **Type:** enhancement
* **Target Area:** MCP generation entrypoints, LM Studio call concurrency, model lifecycle/unload policy
* **Summary:**

  * The review says the MCP generation path is globally serialized and paired with default auto-unload, which makes throughput worst under load.
  * This ticket changes concurrency control so only the scarce LM Studio resource is limited, while non-LM work proceeds concurrently.
  * It also changes the default server-mode lifecycle away from unconditional unload-after-run.
* **In Scope:**

  * Remove process-wide serialization across the whole request pipeline.
  * Keep one concurrency limiter around LM Studio calls.
  * Allow non-LM work to proceed concurrently.
  * Default to keeping the model warm in MCP/server deployment mode.
  * Replace unconditional unload with explicit eviction or idle-timeout behavior.
* **Out of Scope:**

  * Security/path validation work.
  * Analyzer model-authorship changes.
  * Graph evidence/topology work.
* **Current Behavior (Actual):**

  * A process-wide `_lock = threading.Lock()` wraps generation entrypoints.
  * `LMSTUDIO_AUTO_UNLOAD` defaults to `True`.
  * `run_generation()` unloads the model in `finally` when `model_loaded` is true.
* **Expected Behavior:**

  * Request pipelines are not globally serialized.
  * Only LM calls are concurrency-limited.
  * Model state stays warm by default in server/MCP mode unless explicit eviction/idle timeout applies.
* **Reproduction Steps:**

  1. Inspect MCP generation entrypoints and observe `with _lock:` wrapping.
  2. Inspect default unload configuration and unload behavior in `run_generation()`.
  3. Note that one job blocks all others and warm model state is discarded after each run.
* **Requirements / Constraints:**

  * Limit concurrency by scarce LM resource, not by whole request.
  * Keep model warm by default in server deployment mode.
  * Use explicit eviction or idle timeout instead of unconditional unload.
* **Evidence:**

  * Snapshot lines: `3575`, `3703–3758`, `3777–3856`, `3875–3942`, `947–949`, `2794–2796`
  * Review consequence: head-of-line blocking, poor parallelism, high tail latency, wasted startup churn
* **Open Items / Unknowns:**

  * Exact deployment modes and their config split are not provided.
  * Exact idle-timeout/eviction mechanism is not specified in the review.
* **Risks / Dependencies:**

  * More careful LM client lifecycle management is required.
* **Acceptance Criteria:**

  * Generation entrypoints are no longer serialized by a whole-service mutex.
  * Concurrency limiting is applied to LM Studio calls rather than the entire request pipeline.
  * Non-LM request work can proceed concurrently.
  * Server/MCP mode defaults to keeping the model warm rather than unloading after every run.
  * Unload behavior is governed by explicit eviction or idle timeout rather than unconditional per-run unload.
* **Priority & Severity (if inferable from input text):**

  * **Priority:** P2
  * **Severity:** S2
* **Source:**

  * “Throughput is artificially throttled by a global mutex plus default auto-unload”
  * “one job blocks all others”
  * “keep one concurrency limiter around LM Studio calls”

---

## T7 Title: TICKET-070 Add real graph edges that justify analytical graph claims

* **Type:** enhancement
* **Target Area:** Repo graph topology, force-graph edge generation, analytical graph UX
* **Summary:**

  * The review says the current force graph is effectively a star topology and does not support the analytical claims made in the UI.
  * This ticket deepens the topology by adding real edges from repository relationships named in the review, so the graph helps users navigate coupling, reachability, and adjacency rather than functioning as a directory menu.
  * This follows the higher-reward branch explicitly suggested by the review.
* **In Scope:**

  * Add real graph edges instead of MOC-only outward links.
  * Support edge classes named in the review: shared import/dependency clusters, shared package ownership, entry-point-to-subsystem reachability, test-to-code adjacency, docs-to-code references.
  * Ensure `to_force_graph()` materializes meaningful edges from those relationships.
  * Align UI claims with the actual graph structure.
* **Out of Scope:**

  * The fallback “use a list or clustered tree” path.
  * Placeholder evidence cleanup covered by T3.
  * Source-ingestion foundation work covered by T2.
* **Current Behavior (Actual):**

  * Subsystem nodes are created with `links=[]`.
  * Only the MOC node links outward.
  * The force graph is effectively a star.
  * The MOC text promises exploration/dependency/test prompts that the structure does not materially support.
* **Expected Behavior:**

  * The force graph exposes meaningful inter-subsystem edges.
  * Users can navigate actual repository relationships rather than only MOC-to-subsystem links.
  * UI claims about dependency risk review, exploration paths, and test expansion are supportable by the topology.
* **Reproduction Steps:**

  1. Inspect node creation and observe empty subsystem `links`.
  2. Inspect `to_force_graph()` and observe that only existing links become edges.
  3. Compare the resulting star graph against the stronger analytical claims in MOC text.
* **Requirements / Constraints:**

  * Add real edges.
  * Use edge candidates named by the review.
  * Keep graph claims aligned with the actual topology.
* **Evidence:**

  * Snapshot lines: `1880–1891`, `1894–1919`, `1925–1939`
  * Review consequence: visually busy graph that teaches little about coupling, call flow, dependency concentration, or test gaps
* **Open Items / Unknowns:**

  * Exact minimum edge set required for launch is not provided.
  * Exact weighting/visual treatment of new edges is not provided.
* **Risks / Dependencies:**

  * Depends on T2 for stronger extraction signals.
  * Depends on T3 for evidence credibility.
* **Acceptance Criteria:**

  * The force graph is no longer effectively a star topology.
  * Subsystem-to-subsystem edges exist for real repository relationships named in the review.
  * `to_force_graph()` materializes those relationships into actual graph edges.
  * The graph better supports exploration/dependency/test-navigation claims made in the UI.
* **Priority & Severity (if inferable from input text):**

  * **Priority:** P2
  * **Severity:** S2
* **Source:**

  * “The graph topology is too shallow to support the UI claims”
  * “the force graph is effectively a star”
  * “Good edge candidates: shared import/dependency clusters”

# Info-only

* The review positively notes:

  * The LM Studio connectivity layer is comparatively defensive.
  * The run store has sane hygiene: bounded history, TTL cleanup, state timestamps.
  * The path-validation intent is correct; the problem is inconsistent use.
* Assumptions preserved from the review:

  * MCP graph read handlers are assumed reachable by untrusted or semi-trusted callers.
  * The graph is assumed intended for repository understanding, not just UI decoration.
  * The review does not claim reasoning leakage already happened in production; it claims the current flow allows it.
