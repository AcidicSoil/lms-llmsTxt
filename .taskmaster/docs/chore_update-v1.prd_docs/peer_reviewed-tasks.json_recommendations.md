# Task Quality Review Report

## Overall Assessment

The task set provides a reasonable decomposition of a deterministic streaming run architecture (typed events → in-process pub/sub → deterministic terminal controller → pipeline instrumentation → MCP exposure → cancellation → server wiring, plus a post-MVP ODA loop).

Key gaps are (1) missing/implicit PRD success metrics and acceptance criteria (ordering guarantees, latency bounds, memory bounds, cancellation SLA, replayability), (2) a few schema mismatches across tasks (milestone/step events vs `EventType`, token streaming mapped into “progress” without a token-capable payload), (3) unclear concurrency model (asyncio vs threads) across EventBus/Runner/CompletionController, and (4) a spec risk: MCP tool “streaming output” may not be supported as described, depending on client/transport, so the streaming design should be validated against MCP capabilities and/or adapted to notifications/resources. ([GitHub][1])

## Task Reviews

### Task 1: Define Event Models and Schemas

* **Completeness:** Partial
* **Quality:** Mostly clear, needs refinement
* **Issues Identified:**

  * The plan calls for `payload: Union[...]` keyed by `type`, but Pydantic discriminated unions require a discriminator field that exists on the union members (typically each event variant includes `type: Literal[...]`). Without choosing a concrete modeling pattern, deserialization and JSON schema may be fragile.  ([Pydantic][2])
  * `timestamp` defaulting to `datetime.utcnow` produces naive datetimes; this commonly leads to timezone ambiguity in logs/serialization unless constrained/normalized.  ([Pydantic][3])
  * Event types do not cover later task usage (Task 4 milestone names and Task 10 `step.completed/step.failed` expectations).
  * No explicit acceptance criteria for `sequence_number` behavior (who assigns it; monotonicity; gaps allowed).
* **Suggested Improvements:**

  * Pick one explicit event modeling strategy:

    * Prefer: `RunEvent = Annotated[Union[RunStartedEvent, ProgressEvent, ...], Field(discriminator="type")]` with each event model containing `type: Literal["run.started"]`, etc. ([Pydantic][4])
  * Require timezone-aware timestamps (e.g., `AwareDatetime` or enforce UTC) and specify serialization format. ([Pydantic][3])
  * Add/resolve missing event types now (either extend `EventType` to include milestone/step/loop events or map milestones into existing types with a structured payload).
  * Add explicit test assertions for ordering/sequence: monotonic per-run, starting value, and whether gaps are permitted.

### Task 2: Implement In-Process Event Bus

* **Completeness:** Partial
* **Quality:** Ambiguous (concurrency model not pinned down)
* **Issues Identified:**

  * Task text is split between `queue.Queue` vs `asyncio.Queue`, and later tasks introduce worker threads; the bus needs a single, explicit concurrency contract (pure-async, thread-safe bridging, or anyio).
  * “Fan-out” is required, but details don’t specify behavior for slow subscribers (drop policy vs backpressure vs disconnect), nor how `maxsize` is chosen and enforced.
  * `close_run` sentinel/termination semantics are underspecified (e.g., how subscribers detect closure; whether terminal event also closes; race conditions if `close_run` happens before subscribe).
* **Suggested Improvements:**

  * Define an explicit model: e.g., `EventBus.publish()` callable from worker threads, but consumption via async generator; document the bridge (thread → async loop) and test it.
  * Define and test backpressure policy:

    * Option A: block publisher (can deadlock worker).
    * Option B: drop oldest/newest with a “dropped_count” diagnostic event.
    * Option C: per-subscriber disconnect on overflow.
  * Add acceptance criteria: per-run max buffered events, cleanup guarantees after terminal, multi-subscriber ordering invariants.

### Task 3: Implement Completion Controller

* **Completeness:** Partial
* **Quality:** Clear, but missing integration constraints
* **Issues Identified:**

  * State machine is good, but Task 9 partially duplicates/overlaps by reintroducing idempotency/locks and `ensure_terminal_on_exit`.
  * Does not explicitly specify when the run transitions to RUNNING (e.g., who emits `run.started` and when).
  * If EventBus is asyncio-based, locking and publishing across threads needs careful specification (threading lock alone doesn’t solve cross-loop publication).
* **Suggested Improvements:**

  * Consolidate Task 3 + Task 9 requirements: define CompletionController as the single source of terminal emission, including the context-manager guarantee.
  * Add explicit “start” API: `mark_started(inputs)` that emits `run.started` and sets RUNNING (or define where it occurs).
  * Add tests for: “no terminal emitted if already terminal”, and “terminal emission triggers EventBus close_run semantics.”

### Task 4: Refactor Pipeline for Milestone Emission

* **Completeness:** Partial
* **Quality:** Clear, but schema alignment is missing
* **Issues Identified:**

  * Milestone events listed (`repo_fetched`, `analysis_started`, etc.) are not part of the EventType list in Task 1, so the mapping to schema is unclear.
  * The callback signature is undefined: is it raw strings, structured dicts, or typed events?
  * No explicit requirement for preserving deterministic ordering across milestones vs token events.
* **Suggested Improvements:**

  * Define a canonical mapping:

    * Either represent milestones as `progress` with `current_step` values, or introduce `milestone` event type with a `MilestonePayload{name, metadata}`.
  * Specify callback signature precisely and include a “must not change file I/O side effects” regression test using a temp directory or mocked FS.

### Task 5: Integrate DSPy Streaming Hooks

* **Completeness:** Partial
* **Quality:** Needs refinement (token mapping is underspecified)
* **Issues Identified:**

  * Mapping “token generation” to `progress` is ambiguous: progress payload is percentage/current_step, not token deltas; you likely need either `artifact.partial` or a dedicated `token.delta`/`text.delta` event.
  * DSPy streaming should be grounded in the library’s supported pattern (e.g., `streamify`), but the task doesn’t define the exact integration point or expected callback shape. ([DSPy][5])
  * Throttling policy is vague; needs an explicit algorithm and correctness constraints (never lose final output; ensure terminal still emitted).
* **Suggested Improvements:**

  * Update schema or mapping:

    * If you want incremental generated text, use `artifact.partial` with `artifact_id="llms.txt"` / `"llms-full.txt"`, and keep `progress` for coarse milestones.
  * Add an explicit DSPy streaming prototype expectation (what function yields what type) based on current DSPy docs. ([DSPy][5])
  * Define throttling acceptance criteria (max events/sec, worst-case delay, guaranteed final flush).

### Task 6: Implement Streaming MCP Tool

* **Completeness:** Partial
* **Quality:** Ambiguous due to MCP streaming constraints
* **Issues Identified:**

  * The task assumes a tool can “return a generator that yields SSE-formatted events.” MCP tool results may not support streaming in that manner depending on transport/client; MCP discussions note streaming tool results are not universally supported.  ([GitHub][1])
  * If FastMCP wraps/serializes tool outputs, returning SSE lines may be counterproductive; you need a verified client contract (raw SSE vs JSON messages vs notifications).
* **Suggested Improvements:**

  * Add an explicit validation subtask: confirm the MCP client/transport supports streamed tool outputs; if not, redesign as:

    * Tool starts run and returns `run_id`.
    * Server emits progress via MCP notifications or exposes a resource/endpoint to stream events.
  * Add end-to-end tests that reflect the actual MCP transport you’ll ship with (stdio vs streamable HTTP). ([Model Context Protocol][6])

### Task 7: Implement Run Cancellation Support

* **Completeness:** Partial
* **Quality:** Clear, but missing lifecycle details
* **Issues Identified:**

  * “Look up active EventBus/context by run_id” implies a run registry, but no explicit task defines/implements that shared registry and its cleanup policy.
  * Cancellation semantics need an SLA: how quickly the worker must stop; how to handle cancellation after terminal.
* **Suggested Improvements:**

  * Add explicit run registry requirements (in-memory map with TTL; removed on terminal; thread-safe).
  * Add tests for: cancel-before-start, cancel-after-terminal (idempotent no-op), cancel-during-backpressure.

### Task 8: Register Tools and Update Server Entry Point

* **Completeness:** Partial
* **Quality:** Clear
* **Issues Identified:**

  * Relies on “generator-based tools” support without confirming FastMCP’s expectations; this should be validated with the actual FastMCP docs and transport being used.  ([Model Context Protocol][6])
  * “Hybrid RunStore updates” is described, but RunStore schema/locking/versioning isn’t addressed anywhere else.
* **Suggested Improvements:**

  * Add a concrete definition of RunStore responsibilities: minimal fields, update points, retention/cleanup.
  * Replace “Check `mcp list-tools` output” with an executable test harness (spawn server, query tool list via the same client used in production).

### Task 9: Harden Completion Determinism

* **Completeness:** Partial (good intent, overlaps Task 3)
* **Quality:** Clear
* **Issues Identified:**

  * Duplicates CompletionController locking/idempotency and `ensure_terminal_on_exit` that already exist in Task 3 subtasks.
  * “Ignore finish_reason if it conflicts with explicit stream markers” is not testable as written without defining which provider markers exist and the precedence rules.
* **Suggested Improvements:**

  * Merge duplication: make Task 9 about “fault-injection + precedence rules” only, and keep CompletionController implementation in Task 3.
  * Define a precedence table and test matrix: explicit cancel > explicit fail > explicit complete > provider finish_reason. Include example scenarios.

### Task 10: Implement ODA Step Runner (Foundation)

* **Completeness:** Missing elements
* **Quality:** Needs refinement (event model mismatch)
* **Issues Identified:**

  * Task expects `step.completed`/`step.failed` events, but the event schema (Task 1) defines only `run.*` terminal events.
  * It assumes “subscribe to EventBus of the current step”; but EventBus is keyed by `run_id` in prior tasks—no step scoping strategy is defined.
* **Suggested Improvements:**

  * Decide scoping model:

    * Either each step is its own `run_id` (recommended for reuse), and the loop chains runs.
    * Or extend events with `step_id` and add step-level terminal events to the schema.
  * Add minimal PRD-level acceptance criteria: “no polling”, “next step starts only after terminal event”, “cancellation stops chain immediately.”

## Cross-Cutting Recommendations

1. Add explicit PRD-derived acceptance criteria to the relevant tasks (even a short bullet list per task): ordering, terminal uniqueness, max buffer, cleanup guarantees, cancellation latency, and “no polling.”

2. Validate the MCP streaming approach early: if streamed tool results aren’t supported for your target client/transport, pivot to notifications/resources and keep the tool return as the final summary. ([GitHub][1])

3. Align schemas across milestones/tokens/steps:

* milestones → progress/log/milestone event
* tokens/text deltas → artifact.partial or a dedicated delta type
* step events → either per-step run_id or explicit step event types.

[1]: https://github.com/modelcontextprotocol/python-sdk/issues/472 "can we call tools and return steaming output? · Issue #472 · modelcontextprotocol/python-sdk · GitHub"
[2]: https://docs.pydantic.dev/latest/concepts/unions/?utm_source=chatgpt.com "Unions - Pydantic Validation"
[3]: https://docs.pydantic.dev/2.0/usage/types/datetime/?utm_source=chatgpt.com "Datetimes"
[4]: https://docs.pydantic.dev/2.0/usage/types/unions/?utm_source=chatgpt.com "Unions"
[5]: https://dspy.ai/api/utils/streamify/?utm_source=chatgpt.com "dspy.streamify"
[6]: https://modelcontextprotocol.io/docs/develop/build-server "Build an MCP server - Model Context Protocol"
