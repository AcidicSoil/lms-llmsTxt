1. Overview

Problem statement. The current MCP server implementation generates artifacts in a background thread and returns a `run_id` immediately, requiring clients to poll `lmstxt_list_runs` / `lmstxt_read_artifact` to detect completion. This makes it hard to build an automated observe–decide–act (ODA) agent loop that advances deterministically when generation finishes, and it prevents real-time incremental output from being consumed as it is produced.

Target users (assumptions). (1) MCP clients and agent frameworks that want to chain tool calls without polling; (2) CLI users who want visible progress and deterministic “done” signaling; (3) developers integrating LM Studio + DSPy streaming into automation. MCP’s “streamable HTTP” pattern commonly uses SSE to support incremental output. ([The New Stack][1])

Why current solutions fail. Polling-based status checks are non-deterministic under load and add latency; streamed LLM output completion is not reliably inferred from token chunks alone (vendors and libraries vary in where/when `finish_reason` appears). ([GitHub][2])

Success metrics (measurable).

1. Completion determinism: 99.9% of runs emit exactly one terminal completion event (completed|failed|canceled).
2. No polling: reference client can chain ODA steps using only streamed events (no `list_runs` / `read_artifact` required for completion detection).
3. Streaming latency: first progress/event emitted within 500ms of tool invocation (excluding network).
4. Reproducible state transitions: same event sequence categories for the same run phases (enqueue → start → analyze → write → done).

Constraints / integrations / assumptions.

* Python MCP server uses `mcp.server.fastmcp.FastMCP` and a `RunStore`/threaded worker model today.
* LM Studio supports OpenAI-compatible streaming via SSE (`stream: true`). ([LM Studio][3])
* DSPy supports streaming tokens and intermediate status messages via `streamify` and listeners. ([DSPy][4])
* LiteLLM streaming semantics and `finish_reason` placement may vary; completion detection must not rely solely on `finish_reason`. ([LiteLLM][5])

1. Capability Tree (Functional Decomposition)

Capability: Event Model and Run State (FOUNDATION, MVP)
Feature: Run event schema

* Description: Define a typed event envelope for all streamed outputs and state transitions.
* Inputs: `run_id`, timestamp, event type, payload.
* Outputs: Validated event object (serializable).
* Behavior: Enforce a closed set of event types; require a terminal event exactly once.

Feature: Run state reducer

* Description: Compute run status and progress from an event stream deterministically.
* Inputs: Prior state, incoming event.
* Outputs: New state (`pending|processing|completed|failed|canceled`), progress fields.
* Behavior: Terminal events freeze state; invalid transitions rejected and logged.

Capability: Streaming Execution (MVP)
Feature: Event bus (in-process)

* Description: Publish/subscribe events for a run without polling.
* Inputs: Event objects; subscriber registration.
* Outputs: Ordered per-run event stream to subscribers.
* Behavior: Per-run ordering; backpressure via bounded buffers; fan-out to N subscribers.

Feature: Deterministic completion detector

* Description: Determine when a streamed operation is finished and emit a terminal event.
* Inputs: (a) LM/DSPy stream callbacks; (b) worker lifecycle signals; (c) SSE terminators when applicable.
* Outputs: Exactly one of `run.completed` / `run.failed` / `run.canceled`.
* Behavior: Prefer explicit terminators (e.g., SSE `[DONE]` when present); otherwise complete on worker exit; never depend solely on `finish_reason`. ([OpenAI Platform][6])

Feature: Progress + partial output streaming

* Description: Stream incremental status and partial artifacts (or partial text) as they are produced.
* Inputs: DSPy intermediate status, token chunks, pipeline milestones (fetch repo, analyze, render, write).
* Outputs: `progress` events, `log` events, optional `partial_text` events.
* Behavior: Throttle high-frequency token events; always emit milestone events.

Capability: MCP Streaming Interface (MVP)
Feature: Streamed tool invocation

* Description: Add an MCP tool that returns a stream of events for a run rather than only a `run_id`.
* Inputs: repo URL, output_dir, cache flags, stream options.
* Outputs: Event stream + terminal event; also persists artifacts as today.
* Behavior: Starts run, streams events, ends stream after terminal event.

Feature: Backward-compatible non-streaming tools

* Description: Keep existing `lmstxt_generate_*` tools and `RunStore` APIs.
* Inputs: Same as today.
* Outputs: Same JSON `RunRecord` responses.
* Behavior: Internally reuse the same runner; if no streaming subscriber exists, run completes normally.

Capability: Observe–Decide–Act Agent Loop (POST-MVP core)
Feature: ODA step runner

* Description: Execute a sequence of steps where each step starts on a deterministic completion event from the prior step.
* Inputs: Step definitions, initial observation, event streams from tools.
* Outputs: Step results, final run transcript, terminal loop status.
* Behavior: Subscribe to events; on terminal event decide next step; no polling.

Feature: Step graph + guards

* Description: Allow conditional branching and retries based on terminal outcome and metrics.
* Inputs: Terminal event type, error payload, retry policy.
* Outputs: Next step selection or abort.
* Behavior: Bounded retries; emits loop-level terminal event.

Capability: Structured Outputs for Determinism (POST-MVP)
Feature: Structured analysis outputs

* Description: Produce schema-validated analysis fields to reduce downstream ambiguity.
* Inputs: Repo material.
* Outputs: Typed objects for purpose/concepts/structure.
* Behavior: Validate/parse via DSPy adapter patterns; reject invalid outputs.  ([DSPy][7])

1. Repository Structure + Module Definitions (Structural Decomposition)

Existing relevant modules

* `src/lms_llmsTxt/pipeline.py`: synchronous generation orchestration.
* `src/lms_llmsTxt/lmstudio.py`: LM Studio configuration with streaming enabled in `dspy.LM(..., streaming=...)`.
* `src/lms_llmsTxt_mcp/server.py`: MCP tools, background thread spawn, `RunStore`.

Proposed additions (Python)

A) `src/lms_llmsTxt_mcp/events.py`

* Responsibility: Define event types, payload models, and serialization.
* Exports:

  * `RunEvent` (pydantic model)
  * `EventType` enum (e.g., `run.started`, `progress`, `log`, `artifact.partial`, `run.completed`, `run.failed`, `run.canceled`)
  * `TerminalEventTypes`

B) `src/lms_llmsTxt_mcp/event_bus.py`

* Responsibility: In-process pub/sub with per-run channels and bounded buffering.
* Exports:

  * `EventBus.publish(event)`
  * `EventBus.subscribe(run_id) -> EventStream`
  * `EventStream.__iter__/async_iter` (depending on transport needs)
  * `EventBus.close_run(run_id)`

C) `src/lms_llmsTxt_mcp/completion.py`

* Responsibility: Emit exactly-one terminal event per run using explicit signals.
* Exports:

  * `CompletionController`

    * `mark_failed(error)`
    * `mark_completed(metadata)`
    * `mark_canceled(reason)`
    * `ensure_terminal_on_exit()`

D) `src/lms_llmsTxt_mcp/runner.py`

* Responsibility: Execute generation while emitting events (milestones, partial output, artifacts).
* Exports:

  * `run_llmstxt_with_events(repo_url, config, options, bus) -> None`
* Notes: Wraps existing `run_generation` and/or refactors pipeline entrypoints to accept callbacks.

E) `src/lms_llmsTxt_mcp/streaming_tool.py`

* Responsibility: MCP tool handlers that stream events to the client.
* Exports:

  * `lmstxt_generate_llms_txt_stream(...)` (new tool)
  * (optional) `lmstxt_generate_llms_full_stream(...)`, `lmstxt_generate_llms_ctx_stream(...)`

F) `src/lms_llmsTxt_mcp/agent_loop.py` (POST-MVP)

* Responsibility: Observe–decide–act orchestration across tools using event completion.
* Exports:

  * `AgentLoop.run(plan) -> LoopResult`
  * `Step`, `Plan`, `RetryPolicy`

Refactors (minimal surface change)

* `src/lms_llmsTxt_mcp/server.py`: register new streaming tools; keep existing tools unchanged.
* `src/lms_llmsTxt/pipeline.py`: optionally add a callback hook or “event sink” for milestone emission (without changing file outputs).

1. Dependency Chain (layers, explicit “Depends on: […]”)

Foundation layer (no deps)

* `events.py`: Depends on: []
* `completion.py`: Depends on: [`events.py`]
* `event_bus.py`: Depends on: [`events.py`]

Integration layer

* `runner.py`: Depends on: [`event_bus.py`, `completion.py`, existing `lms_llmsTxt.pipeline`]
* `streaming_tool.py`: Depends on: [`runner.py`, `event_bus.py`, existing `server.py` tool registration]

Application layer

* `server.py` (updates only): Depends on: [`streaming_tool.py`, existing `RunStore`]
* `agent_loop.py` (post-MVP): Depends on: [`event_bus.py`, `streaming_tool.py`]

Acyclic note. All dependencies flow from typed event definitions → bus/completion → runner → tool surface → optional agent loop.

1. Development Phases (Phase 0…N; entry/exit criteria; tasks with dependencies + acceptance criteria + test strategy)

Phase 0: Event foundation
Entry criteria: Existing tests pass; no behavioral changes yet.
Tasks:

* Implement `events.py` (depends on: none)

  * Acceptance: can serialize/deserialize all event types; terminal types defined.
  * Test: unit tests validating schema, required fields, and enum closure.
* Implement `completion.py` (depends on: `events.py`)

  * Acceptance: exactly one terminal event emitted even if called multiple times; idempotent.
  * Test: unit tests for “double complete”, “fail then complete”, worker-exit auto-finalization.
* Implement `event_bus.py` (depends on: `events.py`)

  * Acceptance: subscribers receive ordered events; bounded buffer behavior documented and enforced.
  * Test: unit tests for ordering, fan-out, buffer overflow policy.

Exit criteria: A synthetic run can publish events and deterministically end with a single terminal event.

Phase 1: Runner emits events for llms.txt generation (MVP usability)
Entry criteria: Phase 0 complete.
Tasks:

* Add milestone emission to generation path (depends on: `event_bus.py`, `completion.py`)

  * Acceptance: events emitted for: start, repo material gathered, LM configured, analysis started, llms.txt written, optional llms-full written, done/failed.
  * Test: integration test with a stubbed pipeline that forces success and failure paths.
* Integrate DSPy streaming hooks where available (depends on: previous task)

  * Acceptance: status events can be emitted from DSPy program execution (token streaming optional); does not break non-streaming mode.
  * Test: contract test using DSPy `streamify` wrapper (mock listener) to ensure events are forwarded. ([DSPy][4])

Exit criteria: Local subscriber can observe a complete event stream for a real run without polling.

Phase 2: MCP streaming tool surface (MVP completion: no polling)
Entry criteria: Phase 1 complete.
Tasks:

* Implement `lmstxt_generate_llms_txt_stream` tool (depends on: `runner.py`, `event_bus.py`)

  * Acceptance: tool returns streamed events and closes after terminal event; artifacts still persist to disk.
  * Test: end-to-end tool invocation test with a client harness; verify stream terminates and terminal event present.
* Backward compatibility verification (depends on: previous task)

  * Acceptance: existing `lmstxt_generate_llms_txt`/`list_runs`/`read_artifact` unchanged; both paths can coexist.
  * Test: regression tests for existing tools and RunStore behaviors.

Exit criteria: A client can trigger generation and wait for completion without polling.

Phase 3: Deterministic completion hardening (edge cases)
Entry criteria: Phase 2 complete.
Tasks:

* Add explicit SSE/[DONE] and worker-exit completion rules (depends on: `completion.py`)

  * Acceptance: completion is correct even when `finish_reason` is missing/misplaced; terminal event always emitted.
  * Test: unit tests with recorded-like chunk sequences demonstrating `finish_reason` inconsistency. ([GitHub][2])
* Add cancellation support (depends on: `event_bus.py`, `runner.py`)

  * Acceptance: cancel request causes `run.canceled` terminal event; resources cleaned up; artifacts are either absent or clearly marked partial.
  * Test: integration test cancelling mid-run; verify terminal event and stream closure.

Exit criteria: Terminal event is reliable across success/failure/cancel and stream always terminates.

Phase 4: Observe–Decide–Act loop (post-MVP)
Entry criteria: Phase 2 complete (Phase 3 recommended).
Tasks:

* Implement `agent_loop.py` with step chaining based on terminal events (depends on: `streaming_tool.py`)

  * Acceptance: demo plan: generate llms.txt → then generate llms-full → then read artifact; each step starts only after prior terminal event.
  * Test: end-to-end orchestration test with stub steps and forced failures/retries.

Exit criteria: A plan can execute end-to-end without polling and with deterministic step transitions.

1. User Experience

Personas.

* Automation client: wants a single call that yields progress, partial output, and a deterministic “done” signal to chain steps.
* CLI user: wants progress visibility and a clear completion message without needing a second command.

Key flows.

* Streamed generation: client calls streaming tool → receives `run.started` → progress/log/partial events → `run.completed` → stream closes.
* Failure: client receives `run.failed` with error payload; stream closes; optional artifact pointers included.
* Mixed mode: non-streaming tools remain usable; streaming tool is optional.

UI/UX notes.

* Event payloads should be human-readable by default (short `message` field) and machine-parseable (typed payload).
* Rate-limit token events; prefer “status milestones” for usability (DSPy explicitly supports intermediate status streaming). ([DSPy][4])

1. Technical Architecture

System components.

* MCP layer: FastMCP tool handlers (existing + new streaming tool).
* Runner layer: wraps existing generation pipeline, emitting events at milestones and optionally forwarding DSPy streaming.
* Eventing layer: typed events + in-process bus + completion controller.
* LM layer: LM Studio OpenAI-compatible endpoint with streaming SSE when enabled. ([LM Studio][3])
* Optional ODA layer: agent loop that subscribes to events and advances on terminal events.

Completion signaling design (deterministic rules).

* Primary: explicit stream terminator where available (e.g., OpenAI-style SSE `[DONE]`). ([OpenAI Platform][6])
* Secondary: worker lifecycle (thread/async task exit) triggers `ensure_terminal_on_exit()`.
* Tertiary: guard timer only for abnormal transport termination (network drop), emitting `run.failed` with “transport closed” reason.

Streaming source integration.

* DSPy: use `streamify` + listeners for intermediate status and token streaming where supported. ([DSPy][4])
* LM Studio: supports streaming or non-streaming; do not infer completion solely from `finish_reason` due to known inconsistencies across stacks. ([GitHub][2])
* LiteLLM: supports streaming; treat `finish_reason` as advisory only. ([LiteLLM][5])

Data models.

* `RunEvent`: `{run_id, seq, ts, type, message?, payload?}`
* `RunState`: derived via reducer; stored in `RunStore` for compatibility (optional duplication of state is acceptable if reducer is authoritative).

1. Test Strategy

Targets (pyramid).

* Unit: event schema, reducer, completion controller, bus backpressure.
* Integration: runner emits correct milestone sequence for success/failure/cancel; artifacts written.
* End-to-end: MCP streaming tool invocation produces a terminal event and closes stream; non-streaming tools remain unchanged.

Critical scenarios per module.

* `completion.py`: double terminal attempts; terminal on worker exit; fail-before-complete; cancel precedence.
* `event_bus.py`: N subscribers; late subscriber behavior (define: either receives from “now” or replays last K events); buffer overflow policy.
* `runner.py`: exceptions in LM config; fallback path still emits coherent events and terminal.
* Transport semantics: simulate missing/misplaced `finish_reason` sequences to ensure completion still works. ([GitHub][2])

Minimum coverage (assumption).

* ≥80% line coverage on new eventing/streaming modules; integration coverage for at least one real “happy path” and one forced failure path.

1. Risks and Mitigations

Risk: Streaming semantics differ across transports/providers (`finish_reason` placement, chunk shapes).

* Impact: High (breaks determinism).
* Likelihood: Medium.
* Mitigation: Make completion depend on explicit terminators and worker lifecycle, not `finish_reason`; add fixture tests for inconsistent chunk patterns. ([GitHub][2])

Risk: Event flood (token streaming overwhelms clients).

* Impact: Medium.
* Likelihood: Medium.
* Mitigation: Throttle token events; prioritize milestone/status streaming (DSPy supports intermediate status streaming). ([DSPy][4])

Risk: Concurrency hazards with current global lock usage in generator (`_lock`).

* Impact: Medium.
* Likelihood: Medium.
* Mitigation: Keep per-run isolation in bus; minimize global locks; ensure terminal emission is idempotent.

Risk: Backward compatibility with existing MCP clients.

* Impact: Medium.
* Likelihood: Low.
* Mitigation: Add new streaming tools without changing existing tool signatures/behavior.

1. Appendix

Existing codebase references.

* Current MCP server uses background threads and requires polling via `list_runs` / `read_artifact`; artifacts persisted under `./artifacts`.
* DSPy upgrade notes and relevant changes (package naming, streaming and structured output improvements) are captured in your DSPy reference material.

External references.

* OpenAI-style streaming via SSE and explicit termination patterns. ([OpenAI Platform][6])
* LM Studio OpenAI-compatible endpoints and streaming support (`stream: true`). ([LM Studio][3])
* DSPy streaming (`streamify`, token + status streaming). ([DSPy][4])
* `finish_reason` inconsistency in streaming stacks (examples across ecosystems). ([GitHub][2])
* MCP streamable HTTP / SSE discussions and implementation guidance. ([The New Stack][1])

[1]: https://thenewstack.io/how-mcp-uses-streamable-http-for-real-time-ai-tool-interaction/?utm_source=chatgpt.com "How MCP Uses Streamable HTTP for Real-Time AI Tool ..."
[2]: https://github.com/BerriAI/litellm/issues/13348?utm_source=chatgpt.com "[Bug]: finish_reason inconsistency in Async + Streaming #13348"
[3]: https://lmstudio.ai/blog/lmstudio-v0.3.29?utm_source=chatgpt.com "Use OpenAI's Responses API with local models"
[4]: https://dspy.ai/tutorials/streaming/?utm_source=chatgpt.com "Streaming"
[5]: https://docs.litellm.ai/docs/completion/stream?utm_source=chatgpt.com "Streaming + Async"
[6]: https://platform.openai.com/docs/guides/streaming-responses?utm_source=chatgpt.com "Streaming API responses"
[7]: https://dspy.ai/?utm_source=chatgpt.com "DSPy"
