1. Overview

## Problem

`lmstudio-lmstxt-generator` is currently a CLI/library that generates `llms.txt`, `llms-full.txt`, and optionally `llms-ctx.txt` for a given GitHub repo URL.

Goal: wrap this generator as an **MCP server** so MCP clients (IDE agents, chat apps, automation runners) can (a) trigger generation and (b) read the produced artifacts as MCP resources/tools, without re-implementing the pipeline logic.

## Target users

* **Agent/tooling users**: Want a single MCP tool call to produce repository context artifacts and then load them as resources into prompts.
* **Automation/CI users**: Want a stable JSON-typed interface to run generation, capture metadata, and archive artifacts.
* **Local developer workflows**: Want stdio transport for desktop/IDE integration and an HTTP transport for service deployment.

## Why current solutions fail

* CLI-only invocation makes it harder to compose into MCP agent workflows (no typed tool schema, no resource URIs, no chunked reads for large outputs).
* Large `llms-full.txt` can be unsafe to “load all at once” into context; MCP needs guardrails (truncate resources + provide chunked reader).

## Success metrics

* **Reliability**: For valid GitHub repo URLs, `llms.txt` and `llms-full.txt` are always produced (even via fallback path).
* **Correctness**: Returned artifact metadata (size, sha256) matches on-disk files.
* **Safety**: Server prevents writing outside an allowlisted output root; resource reads are capped; stdio transport never writes logs to stdout.
* **Usability**: MCP clients can (1) generate, (2) read small resources directly, (3) chunk-read large artifacts.

## Assumptions

* The existing generator remains the source of truth for artifact content and naming (including fallback JSON).
* LM Studio is locally reachable or otherwise accessible to the host running the MCP server.
* GitHub access tokens may be provided for rate limits/private repos (passed through).

---

1. Capability Tree (Functional Decomposition)

### Capability: Generation Orchestration

Provide MCP tools that trigger the existing generation pipeline.

#### Feature: Generate artifacts (MVP)

* **Description**: Run the generator for a repo URL and produce `llms.txt`, `llms-full.txt`, optional `llms-ctx.txt`, and optional fallback JSON.
* **Inputs**: `repo_url`, `enable_ctx`, `link_style`, `output_dir` (optional), `github_token` (optional), LM Studio overrides (optional), `stamp`, `cache_lm`, `inline_max_chars`.
* **Outputs**: `run_id`, `output_root`, list of artifacts with `uri`, `path`, `bytes`, `sha256`, preview text, truncation flag.
* **Behavior**:

  * Validate repo URL format (GitHub https/ssh).
  * Validate output directory against allowlisted root (if provided).
  * Invoke generator orchestration (`run_generation`) and collect produced files.
  * Compute sha256 and preview/truncation per artifact.

#### Feature: Serialize generation execution (MVP)

* **Description**: Avoid LM/DSPy global configuration races across concurrent requests.
* **Inputs**: generation request.
* **Outputs**: deterministic, non-overlapping generator executions.
* **Behavior**: Use a single in-process lock around generator invocation.

#### Feature: LM Studio connectivity error normalization (MVP)

* **Description**: Convert LM Studio connectivity failures into clear MCP tool errors.
* **Inputs**: generator exception(s).
* **Outputs**: structured tool error message surfaced to client.
* **Behavior**: Catch connectivity error class and raise a single actionable message (keep raw stack traces out of expected failures).

---

### Capability: Artifact Access

Expose generated artifacts through MCP Resources plus chunked reads.

#### Feature: Artifact resource URIs (MVP)

* **Description**: Provide MCP resource URIs for each produced artifact.
* **Inputs**: `run_id`, `artifact_name`.
* **Outputs**: resource URI string (e.g., `lmstxt://runs/{run_id}/{artifact}`).
* **Behavior**: Deterministically format URIs and resolve to on-disk paths via the run registry.

#### Feature: Resource read truncation (MVP)

* **Description**: Prevent accidentally loading multi-megabyte artifacts via resource reads.
* **Inputs**: `run_id`, `artifact_name`, server env `LLMSTXT_MCP_RESOURCE_MAX_CHARS`.
* **Outputs**: text (possibly prefixed with a truncation banner).
* **Behavior**: If file length exceeds cap, return prefix banner + first N chars.

#### Feature: Chunked artifact read tool (MVP)

* **Description**: Read large artifact content in bounded chunks.
* **Inputs**: `run_id`, `artifact_name`, `offset`, `limit`.
* **Outputs**: `text`, `eof`, and echo inputs used.
* **Behavior**: Slice by character offset; clamp negative values to safe bounds; indicate end-of-file.

---

### Capability: Run Management

Track runs and their artifact paths.

#### Feature: In-memory run registry (MVP)

* **Description**: Track generated runs in memory for subsequent reads.
* **Inputs**: `run_id`, output_root, artifact paths.
* **Outputs**: internal mapping used by reads/resources.
* **Behavior**: Store `created_at`, `output_root`, `artifacts` map keyed by artifact name.

#### Feature: List recent runs (MVP)

* **Description**: Return most recent run IDs and artifact URIs.
* **Inputs**: `limit`.
* **Outputs**: array of run summaries.
* **Behavior**: Sort by creation time desc, return up to limit.

#### Feature: Persistent run index (non-MVP)

* **Description**: Survive server restarts by persisting run metadata to disk.
* **Inputs**: run completion events.
* **Outputs**: durable index file(s).
* **Behavior**: Append-only JSONL or small SQLite DB keyed by `run_id`.

---

### Capability: Security & Isolation

Constrain filesystem writes and avoid protocol-breaking output.

#### Feature: Output directory allowlist (MVP)

* **Description**: Prevent `output_dir` path traversal outside an allowlisted root.
* **Inputs**: `output_dir`, env `LLMSTXT_MCP_ALLOWED_ROOT`.
* **Outputs**: validated resolved path or error.
* **Behavior**: Resolve real path; require it to be within allowed root.

#### Feature: StdIO-safe logging (MVP)

* **Description**: Avoid writing to stdout when using stdio transport.
* **Inputs**: logs.
* **Outputs**: logs emitted to stderr only.
* **Behavior**: Configure logger handlers to stderr.

---

### Capability: Transport & Compatibility

Support typical MCP deployment modes.

#### Feature: stdio transport (MVP)

* **Description**: Run MCP server over stdio for desktop/IDE hosts.
* **Inputs**: CLI arg/env selection.
* **Outputs**: MCP server running on stdio.
* **Behavior**: Start server with transport=`stdio`.

#### Feature: streamable-http transport (MVP)

* **Description**: Run MCP server over HTTP for service deployments.
* **Inputs**: CLI arg/env selection.
* **Outputs**: MCP server running over streamable HTTP.
* **Behavior**: Start server with transport=`streamable-http` and JSON responses enabled.

---

1. Repository Structure + Module Definitions (Structural Decomposition)

## Repository structure (proposed)

```
lmstxt-mcp/
├── pyproject.toml
├── README.md
├── src/
│  └── lmstxt_mcp/
│     ├── __init__.py
│     ├── models.py
│     ├── errors.py
│     ├── config.py
│     ├── security.py
│     ├── hashing.py
│     ├── runs.py
│     ├── artifacts.py
│     └── server.py
└── tests/
   ├── test_security.py
   ├── test_hashing.py
   ├── test_runs.py
   ├── test_artifacts.py
   └── test_server_tools.py
```

> Note: `__init__.py`, `models.py`, and `server.py` exist in the current scaffold; other modules are additions to enforce single-responsibility boundaries.

## Module definitions

### Module: `lmstxt_mcp.models`

* **Maps to capability**: Artifact Access, Run Management
* **Responsibility**: Typed request/response models and shared type literals.
* **Exports**:

  * `ArtifactName`
  * `ArtifactRef`
  * `GenerateResult`
  * `ReadArtifactResult`

### Module: `lmstxt_mcp.errors`

* **Maps to capability**: Generation Orchestration, Security & Isolation
* **Responsibility**: Define server-local exception types and error normalization helpers.
* **Exports**:

  * `InvalidRepoURLError`
  * `OutputDirNotAllowedError`
  * `UnknownRunError`
  * `ArtifactNotFoundError`
  * `LMStudioUnavailableError`

### Module: `lmstxt_mcp.config`

* **Maps to capability**: Security & Isolation, Transport & Compatibility
* **Responsibility**: Read and validate server-level configuration (env + defaults).
* **Exports**:

  * `ServerConfig` (allowed root, resource cap, preview cap, log level)
  * `load_server_config()`

### Module: `lmstxt_mcp.security`

* **Maps to capability**: Security & Isolation
* **Responsibility**: Path validation and allowlist enforcement.
* **Exports**:

  * `validate_output_dir(output_dir: str | None) -> Path | None`

### Module: `lmstxt_mcp.hashing`

* **Maps to capability**: Generation Orchestration
* **Responsibility**: File hashing and text preview extraction.
* **Exports**:

  * `sha256_file(path: Path) -> str`
  * `read_text_preview(path: Path, max_chars: int) -> (str, bool)`

### Module: `lmstxt_mcp.runs`

* **Maps to capability**: Run Management
* **Responsibility**: Store and query run registry (in-memory for MVP).
* **Exports**:

  * `RunRecord`
  * `RunStore` (`put_run`, `get_run`, `list_runs`)

### Module: `lmstxt_mcp.artifacts`

* **Maps to capability**: Artifact Access
* **Responsibility**: Resolve artifact names to paths, build URIs, read/truncate/chunk content.
* **Exports**:

  * `resource_uri(run_id, artifact) -> str`
  * `read_resource_text(run_id, artifact, max_chars) -> str`
  * `read_artifact_chunk(run_id, artifact, offset, limit) -> ReadArtifactResult`

### Module: `lmstxt_mcp.server`

* **Maps to capability**: Transport & Compatibility, Generation Orchestration
* **Responsibility**: Define MCP tools/resources and wire them to the generator + internal modules.
* **Exports**:

  * `mcp` (FastMCP instance)
  * Tool fns: `lmstxt_generate`, `lmstxt_list_runs`, `lmstxt_read_artifact`
  * Resource handler: `lmstxt://runs/{run_id}/{artifact}`

### External dependency: `lmstudiotxt_generator` (existing)

* **Responsibility**: Fetch repo material from GitHub, run DSPy analysis, write artifacts, and build `llms-full.txt`.
* **Key entrypoints used by MCP**:

  * `owner_repo_from_url`
  * `AppConfig`
  * `run_generation`

---

1. Dependency Chain (layers, explicit “Depends on: […]”)

### Foundation layer

* **`lmstxt_mcp.models`**: No dependencies
* **`lmstxt_mcp.errors`**: Depends on: [`lmstxt_mcp.models`] (for consistent naming/types)
* **`lmstxt_mcp.config`**: Depends on: [`lmstxt_mcp.errors`]
* **`lmstxt_mcp.security`**: Depends on: [`lmstxt_mcp.config`, `lmstxt_mcp.errors`]
* **`lmstxt_mcp.hashing`**: Depends on: [`lmstxt_mcp.errors`]

### Run management layer

* **`lmstxt_mcp.runs`**: Depends on: [`lmstxt_mcp.models`, `lmstxt_mcp.errors`]

### Artifact access layer

* **`lmstxt_mcp.artifacts`**: Depends on: [`lmstxt_mcp.models`, `lmstxt_mcp.errors`, `lmstxt_mcp.hashing`, `lmstxt_mcp.runs`, `lmstxt_mcp.config`]

### Integration/orchestration layer

* **`lmstxt_mcp.server`**: Depends on: [`lmstxt_mcp.config`, `lmstxt_mcp.security`, `lmstxt_mcp.hashing`, `lmstxt_mcp.runs`, `lmstxt_mcp.artifacts`, external `lmstudiotxt_generator`]

Acyclic by construction: all arrows point from higher layers to lower layers.

---

1. Development Phases (Phase 0…N; entry/exit criteria; tasks with dependencies + acceptance criteria + test strategy)

### Phase 0: Foundation modules

**Entry criteria**: Repository builds; formatter/linter (if used) runs; test runner wired.
**Tasks (parallelizable)**:

* [ ] Implement `models` (depends on: none)

  * Acceptance: Pydantic models cover tool outputs; artifact name literal includes `llms.txt`, `llms-full.txt`, `llms-ctx.txt`, `llms.json`.
  * Tests: unit tests for model validation (invalid artifact name rejected).
* [ ] Implement `errors` (depends on: [`models`])

  * Acceptance: All error cases map to explicit exception types.
  * Tests: unit tests that each error string is user-actionable.
* [ ] Implement `config` (depends on: [`errors`])

  * Acceptance: Env vars parsed; defaults set (allowed root, resource cap).
  * Tests: unit tests for env parsing, invalid values.
* [ ] Implement `security` (depends on: [`config`, `errors`])

  * Acceptance: Output dir outside allowed root is rejected.
  * Tests: path traversal tests (`..`, symlinks if applicable).
* [ ] Implement `hashing` (depends on: [`errors`])

  * Acceptance: sha256 + preview truncation works for UTF-8 and replacement behavior.
  * Tests: golden hash test with fixture file; preview truncation boundaries.

**Exit criteria**: All foundation modules importable; unit tests green.

---

### Phase 1: Minimal usable MCP server (MVP end-to-end)

**Goal**: A client can generate and retrieve artifacts.
**Entry criteria**: Phase 0 complete.

**Tasks (ordered by deps, parallelizable where possible)**:

* [ ] Implement `runs` store (depends on: [`models`, `errors`])

  * Acceptance: can `put/get/list`; ordering by created_at supported.
  * Tests: in-memory store behavior, unknown run errors.
* [ ] Implement `artifacts` (depends on: [`models`, `errors`, `hashing`, `runs`, `config`])

  * Acceptance: resource URI format stable; chunk reads return eof correctly; resource truncation banner emitted.
  * Tests: offset/limit boundary tests; truncation tests.
* [ ] Implement `server` tools/resources wiring (depends on: Phase 0 + `runs` + `artifacts` + generator integration)

  * Acceptance:

    * Tool `lmstxt_generate` calls generator and returns metadata + URIs.
    * Resource `lmstxt://runs/{run_id}/{artifact}` reads and truncates.
    * Tool `lmstxt_read_artifact` returns chunked content.
    * Logs go to stderr (stdio-safe).
  * Tests:

    * Integration test with a stubbed `run_generation` (monkeypatch) that writes fixture files and verifies metadata + reads.
    * Contract test: tool schemas include all documented inputs/outputs.

**Exit criteria**: Running server + calling generate + reading resources works in a single process.

**Delivers**: Usable MCP server for local/IDE integration (stdio) and service mode (HTTP).

---

### Phase 2: Hardening and operational controls (still MVP-compatible)

**Entry criteria**: Phase 1 complete.

**Tasks**:

* [ ] Add request-level limits (depends on: `server`, `config`)

  * Acceptance: max `inline_max_chars`, max chunk `limit` enforced with safe defaults.
  * Tests: limit clamp behavior.
* [ ] Add optional persistent run index (depends on: `runs`, `config`)

  * Acceptance: server restart can rehydrate runs (feature-flagged).
  * Tests: write/read index file fixtures.
* [ ] Improve error normalization surface (depends on: `errors`, `server`)

  * Acceptance: LM Studio unreachable error is distinguishable from GitHub 404/private token errors.
  * Tests: simulated exceptions mapped to correct error messages.

**Exit criteria**: Server remains stable under repeated runs; memory growth is bounded or observable.

---

### Phase 3: Deployment packaging

**Entry criteria**: Phase 2 complete.

**Tasks**:

* [ ] Packaging + console script verification (depends on: `server`)

  * Acceptance: `lmstxt-mcp` entrypoint works; both transports runnable.
  * Tests: smoke test invoking module main under a subprocess harness.
* [ ] Documentation for configuration + examples (depends on: `config`, `server`)

  * Acceptance: README documents env vars and typical MCP tool usage patterns.

**Exit criteria**: Reproducible install + run instructions validated.

---

1. User Experience

## Personas

* **IDE Agent**: Calls `lmstxt_generate(repo_url)` then loads `llms.txt` resource to decide what to read next; uses chunk tool for `llms-full.txt`.
* **Ops/Automation**: Runs HTTP transport in a service; calls generate for multiple repos; records hashes for change detection.

## Key flows

1. **Generate**

   * User/agent calls `lmstxt_generate` with a GitHub repo URL and optional flags.
   * Receives `run_id` + artifact list (URI + metadata + preview).
2. **Read small artifacts**

   * Client reads `lmstxt://runs/{run_id}/llms.txt` as a resource.
3. **Read large artifacts**

   * Client uses `lmstxt_read_artifact(run_id="...", artifact="llms-full.txt", offset=..., limit=...)` iteratively.
4. **List runs**

   * Client calls `lmstxt_list_runs(limit=...)` to rediscover previous outputs.

## UI/UX notes (protocol-facing)

* Prefer returning previews inline (bounded) to help clients decide what to load.
* Always provide resource URIs for the full artifacts, even when previews are truncated.
* When resource read is truncated, include an explicit banner instructing chunked reads.

---

1. Technical Architecture

## System components

* **MCP Server (FastMCP)**: Defines tools/resources, transport selection, JSON responses.
* **Run store**: Maps `run_id` → output_root + artifact paths (MVP: memory).
* **Generator integration**: Calls existing `run_generation(repo_url, AppConfig, ...)` which:

  * fetches repo tree/README/package files from GitHub,
  * runs DSPy pipeline or falls back,
  * writes artifacts under `artifacts/<owner>/<repo>/`.
* **Artifact IO**: Hashing, preview generation, resource truncation, chunk reads.

## Data models

* `GenerateResult`: `run_id`, repo owner/repo, output_root, `created_at`, list of `ArtifactRef`, notes.
* `ArtifactRef`: `name`, `uri`, `path`, `bytes`, `sha256`, `preview`, `truncated`.
* `ReadArtifactResult`: `offset`, `limit`, `eof`, `text`.

## MCP APIs

* **Tools**

  * `lmstxt_generate(...) -> GenerateResult`
  * `lmstxt_read_artifact(run_id, artifact, offset, limit) -> ReadArtifactResult`
  * `lmstxt_list_runs(limit) -> {count, runs[]}`
* **Resources**

  * `lmstxt://runs/{run_id}/{artifact}` → capped text read

## Key decisions (with rationale)

* **Lock around generation**: DSPy/LM configuration is global; serialize generator calls to avoid cross-request races.
* **Resource truncation + chunk tool**: Prevent clients from accidentally pulling multi-MB artifacts; chunking provides safe access.
* **Output allowlist**: Prevent arbitrary filesystem writes via `output_dir`.

## Trade-offs and alternatives

* **In-memory run store (MVP)**: Simple but loses history on restart; Phase 2 introduces persistence.
* **Character-based chunking**: Simpler than byte ranges; may not align with some downstream byte-oriented tooling.

---

1. Test Strategy

## Test pyramid targets

* **Unit**: 70% (path validation, hashing, preview truncation, chunk slicing, URI formatting)
* **Integration**: 25% (server tool wiring with stubbed generator; resource handler end-to-end)
* **E2E/Smoke**: 5% (launch server in stdio/http in CI and execute one generate+read with fixtures)

## Coverage minimums

* Line: ≥ 85%
* Branch: ≥ 75% (focus on error paths: invalid output dir, unknown run, missing artifact, truncation behavior)

## Critical scenarios (by module)

* `security`

  * Happy: output_dir within allowed root accepted
  * Error: output_dir outside allowed root rejected (including `..` and absolute paths)
* `artifacts`

  * Happy: chunk reads return correct text and eof
  * Edge: negative offset/limit clamps; offset beyond EOF yields empty + eof
  * Resource truncation emits banner and first N chars
* `server`

  * Happy: generate returns run_id + URIs; resource reads resolve
  * Error: LM Studio unreachable → actionable tool error; unknown run_id → clear error
* Integration points

  * Stub generator writes known files; server computes correct sha256 and bytes.

---

1. Risks and Mitigations

## Technical risks

* **LM Studio availability/compatibility**

  * Impact: High; generation fails.
  * Likelihood: Medium.
  * Mitigation: Clear error normalization; encourage fallback artifacts where applicable; document required LM Studio setup.
  * Fallback: If LM fails, generator already produces fallback artifacts and `llms-full.txt` from curated links.

* **Large `llms-full.txt` memory usage**

  * Impact: Medium (OOM on huge files).
  * Likelihood: Medium.
  * Mitigation: Resource truncation; chunked reads; enforce max chunk size.
  * Fallback: Add streaming/seek-based reading in Phase 2 if needed.

* **Run registry growth**

  * Impact: Medium.
  * Likelihood: Medium for long-lived servers.
  * Mitigation: cap stored runs; optional persistence; eviction policy.

## Dependency risks

* **Generator API drift**

  * Impact: Medium.
  * Likelihood: Low/Medium.
  * Mitigation: Pin compatible generator versions; adapter layer; integration tests that fail on signature drift.

* **GitHub rate limits / private repo access**

  * Impact: Medium.
  * Likelihood: Medium.
  * Mitigation: Accept token parameter; pass-through to generator config.

## Scope risks

* **Over-building persistence/auth too early**

  * Impact: Medium.
  * Likelihood: Medium.
  * Mitigation: Keep MVP to generate+read; defer persistence/auth to later phases behind flags.

---

1. Appendix

## Inputs still needed (answering these will refine metrics/scope; not required for MVP)

* Expected deployment mode priority: desktop/stdio only, or HTTP service as primary?
* Any hard limits on artifact size and run retention?
* Need authentication/authorization for HTTP transport (beyond network perimeter)?

## References (provided context)

* MCP wrapper concept and exposed tools/resources.
* Current MCP scaffold (`lmstxt_generate`, chunked reads, resource truncation, stderr logging).
* Existing generator pipeline, artifact outputs, fallback behavior, and GitHub integration.
* Project README for generator usage and prerequisites.
