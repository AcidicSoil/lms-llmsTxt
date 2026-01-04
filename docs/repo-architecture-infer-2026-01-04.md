# Repository Map (hierarchical)
Module: src/lmstudiotxt_generator/
Purpose: Core library that exposes the LM Studio llms.txt generation toolkit as a Python package.
Responsibilities: Export public API surface; aggregate generator/analyzer/config/schema utilities.
Public surface: Package exports via __all__ (AppConfig, RepositoryAnalyzer, GenerationArtifacts, RepositoryMaterial, configure_lmstudio_lm, fallback helpers, LLMS_JSON_SCHEMA).
Evidence: src/lmstudiotxt_generator/__init__.py:{__all__, AppConfig, RepositoryAnalyzer, GenerationArtifacts, RepositoryMaterial, configure_lmstudio_lm, LMStudioConnectivityError, fallback_llms_payload, fallback_llms_markdown, LLMS_JSON_SCHEMA}

Module: ├─ src/lmstudiotxt_generator/cli.py
Purpose: CLI entrypoint for running generation against a repository URL.
Responsibilities: Parse args, populate AppConfig, call run_generation, print artifact summary.
Public surface: build_parser(), main(argv=None).
Evidence: src/lmstudiotxt_generator/cli.py:{build_parser, main}

Module: ├─ src/lmstudiotxt_generator/pipeline.py
Purpose: Orchestrate end-to-end generation workflow.
Responsibilities: Gather repo material, configure LM Studio/DSPy, run analyzer, fallback on LM errors, write llms.txt/ctx/full/json artifacts.
Public surface: run_generation(...), prepare_repository_material(...).
Evidence: src/lmstudiotxt_generator/pipeline.py:{run_generation, prepare_repository_material, _write_text}

Module: ├─ src/lmstudiotxt_generator/analyzer.py
Purpose: DSPy-driven repository analysis and llms.txt rendering.
Responsibilities: Build dynamic doc buckets, validate curated URLs, generate llms.txt markdown.
Public surface: RepositoryAnalyzer, build_dynamic_buckets(...), render_llms_markdown(...).
Evidence: src/lmstudiotxt_generator/analyzer.py:{RepositoryAnalyzer, build_dynamic_buckets, render_llms_markdown, _url_alive}

Module: ├─ src/lmstudiotxt_generator/github.py
Purpose: GitHub API adapter for repository metadata, file tree, and file content.
Responsibilities: Resolve owner/repo, fetch metadata/default branch, fetch tree, read README and package files, fetch content by path.
Public surface: gather_repository_material(...), owner_repo_from_url(...), construct_github_file_url(...).
Evidence: src/lmstudiotxt_generator/github.py:{gather_repository_material, owner_repo_from_url, fetch_file_tree, fetch_file_content, construct_github_file_url}

Module: ├─ src/lmstudiotxt_generator/lmstudio.py
Purpose: LM Studio connectivity and model lifecycle management.
Responsibilities: Probe models, load/unload model via HTTP/SDK/CLI, configure DSPy LM.
Public surface: configure_lmstudio_lm(...), unload_lmstudio_model(...), LMStudioConnectivityError.
Evidence: src/lmstudiotxt_generator/lmstudio.py:{configure_lmstudio_lm, unload_lmstudio_model, LMStudioConnectivityError, _ensure_lmstudio_ready}

Module: ├─ src/lmstudiotxt_generator/full_builder.py
Purpose: Build llms-full content by expanding curated links into full text blocks.
Responsibilities: Fetch GitHub or website content, resolve intra-doc links, append discovered links, truncate large files.
Public surface: build_llms_full_from_repo(...).
Evidence: src/lmstudiotxt_generator/full_builder.py:{build_llms_full_from_repo, parse_github_link, gh_get_file, fetch_raw_file, _extract_links}

Module: ├─ src/lmstudiotxt_generator/fallback.py
Purpose: Heuristic generation path when LM calls fail.
Responsibilities: Produce fallback JSON payload and markdown using file tree + README.
Public surface: fallback_llms_payload(...), fallback_markdown_from_payload(...), fallback_llms_markdown(...).
Evidence: src/lmstudiotxt_generator/fallback.py:{fallback_llms_payload, fallback_markdown_from_payload, fallback_llms_markdown}

Module: ├─ src/lmstudiotxt_generator/config.py
Purpose: Runtime configuration source for LM Studio, GitHub, and output paths.
Responsibilities: Read env vars, provide defaults, create output root.
Public surface: AppConfig.ensure_output_root(...).
Evidence: src/lmstudiotxt_generator/config.py:{AppConfig, ensure_output_root}

Module: ├─ src/lmstudiotxt_generator/models.py
Purpose: Data models for repository material and artifact outputs.
Responsibilities: Define RepositoryMaterial and GenerationArtifacts dataclasses.
Public surface: RepositoryMaterial, GenerationArtifacts.
Evidence: src/lmstudiotxt_generator/models.py:{RepositoryMaterial, GenerationArtifacts}

Module: ├─ src/lmstudiotxt_generator/schema.py
Purpose: JSON schema definition for fallback payloads.
Responsibilities: Provide LLMS_JSON_SCHEMA structure.
Public surface: LLMS_JSON_SCHEMA.
Evidence: src/lmstudiotxt_generator/schema.py:{LLMS_JSON_SCHEMA}

Module: ├─ src/lmstudiotxt_generator/signatures.py
Purpose: DSPy signatures and lightweight fallback mock.
Responsibilities: Define AnalyzeRepository/AnalyzeCodeStructure/GenerateUsageExamples/GenerateLLMsTxt signatures.
Public surface: AnalyzeRepository, AnalyzeCodeStructure, GenerateUsageExamples, GenerateLLMsTxt, dspy shim.
Evidence: src/lmstudiotxt_generator/signatures.py:{AnalyzeRepository, AnalyzeCodeStructure, GenerateUsageExamples, GenerateLLMsTxt}

Module: src/llmstxt_mcp/
Purpose: MCP server wrapper that exposes generation as tools and resources.
Responsibilities: Define MCP tools, store run metadata, serve artifacts.
Public surface: FastMCP tools (llmstxt_generate, llmstxt_list_runs, llmstxt_read_artifact) and resource handler.
Evidence: src/llmstxt_mcp/server.py:{mcp, generate, list_runs, read_artifact, get_run_artifact}

Module: ├─ src/llmstxt_mcp/server.py
Purpose: FastMCP server entrypoint.
Responsibilities: Register MCP tools/resources and run server.
Public surface: generate(), list_runs(), read_artifact(), get_run_artifact(), main().
Evidence: src/llmstxt_mcp/server.py:{generate, list_runs, read_artifact, get_run_artifact, main}

Module: ├─ src/llmstxt_mcp/generator.py
Purpose: Thread-safe MCP wrapper around run_generation.
Responsibilities: Generate artifacts, compute hashes, record run metadata, map LM errors to MCP errors.
Public surface: safe_generate(...).
Evidence: src/llmstxt_mcp/generator.py:{safe_generate}

Module: ├─ src/llmstxt_mcp/runs.py
Purpose: In-memory run history store.
Responsibilities: Store, retrieve, list GenerateResult entries.
Public surface: RunStore.put_run(...), RunStore.get_run(...), RunStore.list_runs(...).
Evidence: src/llmstxt_mcp/runs.py:{RunStore, put_run, get_run, list_runs}

Module: ├─ src/llmstxt_mcp/artifacts.py
Purpose: Artifact access helpers for MCP tools/resources.
Responsibilities: Read artifact text preview or chunk, build resource URI.
Public surface: read_resource_text(...), read_artifact_chunk(...), resource_uri(...).
Evidence: src/llmstxt_mcp/artifacts.py:{read_resource_text, read_artifact_chunk, resource_uri}

Module: ├─ src/llmstxt_mcp/config.py
Purpose: MCP server configuration via pydantic settings.
Responsibilities: Provide allowed root and max chars for resource reads.
Public surface: Settings, settings.
Evidence: src/llmstxt_mcp/config.py:{Settings, settings}

Module: ├─ src/llmstxt_mcp/models.py
Purpose: MCP-facing data models for runs and artifact responses.
Responsibilities: Define ArtifactName literals and GenerateResult/ArtifactRef/ReadArtifactResult models.
Public surface: ArtifactName, GenerateResult, ArtifactRef, ReadArtifactResult.
Evidence: src/llmstxt_mcp/models.py:{ArtifactName, GenerateResult, ArtifactRef, ReadArtifactResult}

Module: ├─ src/llmstxt_mcp/hashing.py
Purpose: Hashing and text preview utilities for artifacts.
Responsibilities: Compute SHA256, read text preview with truncation.
Public surface: sha256_file(...), read_text_preview(...).
Evidence: src/llmstxt_mcp/hashing.py:{sha256_file, read_text_preview}

Module: ├─ src/llmstxt_mcp/security.py
Purpose: Output directory validation helper.
Responsibilities: Enforce allowed output root for MCP outputs.
Public surface: validate_output_dir(...).
Evidence: src/llmstxt_mcp/security.py:{validate_output_dir}

Module: ├─ src/llmstxt_mcp/errors.py
Purpose: MCP error types.
Responsibilities: Define OutputDirNotAllowedError, LMStudioUnavailableError, UnknownRunError.
Public surface: OutputDirNotAllowedError, LMStudioUnavailableError, UnknownRunError.
Evidence: src/llmstxt_mcp/errors.py:{OutputDirNotAllowedError, LMStudioUnavailableError, UnknownRunError}

Module: tests/
Purpose: Test suite (details not inspected in this run).
Responsibilities: Unknown (missing file contents).
Public surface: Unknown (missing file contents).
Evidence: Unknown (missing file contents: tests/*.py)
MissingInput: tests/*.py

Coverage: scripts/, dist/, node_modules/, and tests/ were not inspected beyond listing; module internals there are Unknown.

# Module Table
| Module | Type | Purpose | Key Dependencies (internal + external) | Main Inputs → Outputs | Extensibility Points | Boundary Notes | Evidence |
|---|---|---|---|---|---|---|---|
| src/lmstudiotxt_generator/cli.py | Adapter/Glue | CLI entrypoint for generation. | Internal: pipeline.run_generation, AppConfig. External: argparse. | repo URL + flags → artifact paths summary. | CLI flags via build_parser() for model/base URL/API key/output/link style/stamp/no-ctx/cache. | CLI directly calls pipeline without preflight validation of external services. | Evidence: src/lmstudiotxt_generator/cli.py:{build_parser, main} |
| src/lmstudiotxt_generator/pipeline.py | Glue/Orchestration | End-to-end generation orchestration. | Internal: analyzer, github, lmstudio, fallback, full_builder, models, schema, config. External: litellm exceptions, pathlib. | repo_url + AppConfig → GenerationArtifacts + filesystem writes. | Add new artifact writers or flags inside run_generation; uses GenerationArtifacts model. | Orchestrator mixes LM calls, network fetches, and filesystem writes in one function. | Evidence: src/lmstudiotxt_generator/pipeline.py:{run_generation, prepare_repository_material, _write_text} |
| src/lmstudiotxt_generator/analyzer.py | Domain (with I/O) | Analyze repo metadata and render llms.txt markdown. | Internal: github.construct_github_file_url, signatures. External: dspy, requests. | file_tree/readme/package_files → llms_txt_content. | Adjust taxonomy/buckets; validate_urls toggle in build_dynamic_buckets. | URL validation does network I/O inside analysis, coupling content synthesis to HTTP availability. | Evidence: src/lmstudiotxt_generator/analyzer.py:{RepositoryAnalyzer, build_dynamic_buckets, _url_alive} |
| src/lmstudiotxt_generator/github.py | Adapter/Infra | GitHub API access for repo material. | External: requests. | repo_url/token → file_tree/readme/package files/metadata. | Extend package file candidates list; support more SCMs by adding adapters. | Hard-coded GitHub URLs; no abstraction for alternate hosts. | Evidence: src/lmstudiotxt_generator/github.py:{gather_repository_material, fetch_file_tree, fetch_file_content, get_repository_metadata} |
| src/lmstudiotxt_generator/lmstudio.py | Adapter/Infra | LM Studio model discovery/load/unload + DSPy LM config. | External: requests, subprocess, lmstudio SDK, dspy. | AppConfig → configured dspy.LM; raises LMStudioConnectivityError. | Add new endpoint patterns or SDK behaviors via _MODEL/_LOAD/_UNLOAD lists. | Multiple load/unload strategies increase surface area for failure handling. | Evidence: src/lmstudiotxt_generator/lmstudio.py:{configure_lmstudio_lm, _ensure_lmstudio_ready, _load_model_http, _load_model_cli, unload_lmstudio_model} |
| src/lmstudiotxt_generator/full_builder.py | Glue/Adapter | Build llms-full by fetching curated links and extracting sub-links. | Internal: github._normalize_repo_path. External: requests. | curated llms.txt → llms-full text. | Adjust max_files/max_bytes; change link_style or extraction rules. | Mixes HTML parsing, link resolution, and network fetching in one module. | Evidence: src/lmstudiotxt_generator/full_builder.py:{build_llms_full_from_repo, _extract_links, _fetch_website} |
| src/lmstudiotxt_generator/fallback.py | Domain/Utility | Fallback JSON + markdown generation. | Internal: analyzer, schema. | file_tree/readme → fallback payload + markdown. | Extend schema fields or remember-bullets in fallback helpers. | Fallback path depends on analyzer bucket builder (still hits URL validation). | Evidence: src/lmstudiotxt_generator/fallback.py:{fallback_llms_payload, fallback_markdown_from_payload} |
| src/lmstudiotxt_generator/config.py | Infra | Environment-driven configuration. | External: dotenv. | env vars → AppConfig fields; output root creation. | Add new env vars in AppConfig fields. | Output root creation is side-effectful (mkdir) inside config. | Evidence: src/lmstudiotxt_generator/config.py:{AppConfig, ensure_output_root} |
| src/lmstudiotxt_generator/models.py | Utility | Data carriers for inputs/outputs. | None (dataclasses). | repo material + artifact paths → typed containers. | Extend dataclasses to track more fields. | None noted. | Evidence: src/lmstudiotxt_generator/models.py:{RepositoryMaterial, GenerationArtifacts} |
| src/lmstudiotxt_generator/schema.py | Utility | JSON schema for fallback payloads. | None. | None → LLMS_JSON_SCHEMA constant. | Extend schema to include more sections. | None noted. | Evidence: src/lmstudiotxt_generator/schema.py:{LLMS_JSON_SCHEMA} |
| src/lmstudiotxt_generator/signatures.py | Utility | DSPy signature definitions + local dspy shim. | External: dspy (optional). | repo/file_tree/package_files → analysis outputs. | Extend signatures to include more fields. | MockDSPy path is permissive; may hide missing dspy errors in some contexts. | Evidence: src/lmstudiotxt_generator/signatures.py:{AnalyzeRepository, AnalyzeCodeStructure, GenerateUsageExamples, GenerateLLMsTxt, MockDSPy} |
| src/llmstxt_mcp/server.py | Adapter/Glue | MCP server exposing generation + artifact reads. | Internal: config, models, runs, generator, artifacts. External: mcp FastMCP. | MCP tool calls → JSON strings + resources. | Add new tools via @mcp.tool functions. | MCP outputs are JSON strings (not typed responses). | Evidence: src/llmstxt_mcp/server.py:{mcp, generate, list_runs, read_artifact, get_run_artifact} |
| src/llmstxt_mcp/generator.py | Glue | Thread-safe generator + run recording. | Internal: pipeline.run_generation, RunStore, hashing. | repo_url/output_dir → GenerateResult in run store. | Extend artifact refs or validation logic inside safe_generate. | Output dir validation helper exists but is not invoked here. | Evidence: src/llmstxt_mcp/generator.py:{safe_generate}; Evidence: src/llmstxt_mcp/security.py:{validate_output_dir} |
| src/llmstxt_mcp/runs.py | Utility/Memory | In-memory store for run history. | Internal: models.GenerateResult. | run_id → GenerateResult; list_runs() → list. | Swap with persistent store. | No persistence; data lost on server restart. | Evidence: src/llmstxt_mcp/runs.py:{RunStore, put_run, get_run, list_runs} |
| src/llmstxt_mcp/artifacts.py | Utility | Artifact reading helpers. | Internal: config.settings, RunStore, hashing. | run_id + artifact_name → text/chunk. | Add new artifact access patterns. | Reads assume UTF-8; binary returns placeholder string. | Evidence: src/llmstxt_mcp/artifacts.py:{read_resource_text, read_artifact_chunk} |
| src/llmstxt_mcp/config.py | Infra | MCP settings. | External: pydantic_settings. | env vars → settings. | Add new MCP env settings. | None noted. | Evidence: src/llmstxt_mcp/config.py:{Settings, settings} |
| src/llmstxt_mcp/models.py | Utility | MCP data models. | External: pydantic. | ArtifactName/GenerateResult → JSON serialization. | Extend ArtifactName for new artifacts. | ArtifactName is a closed Literal; new artifacts require update. | Evidence: src/llmstxt_mcp/models.py:{ArtifactName, GenerateResult, ArtifactRef} |
| src/llmstxt_mcp/hashing.py | Utility | Hashing + preview. | External: hashlib. | file path → sha256 + preview. | Adjust chunk size behavior. | None noted. | Evidence: src/llmstxt_mcp/hashing.py:{sha256_file, read_text_preview} |
| src/llmstxt_mcp/security.py | Utility | Output directory validation. | Internal: config.settings. | path → resolved path or OutputDirNotAllowedError. | Enforce server-side output constraints. | Not wired into generation path. | Evidence: src/llmstxt_mcp/security.py:{validate_output_dir} |
| src/llmstxt_mcp/errors.py | Utility | Error types. | None. | None. | Extend error taxonomy. | None noted. | Evidence: src/llmstxt_mcp/errors.py:{OutputDirNotAllowedError, LMStudioUnavailableError, UnknownRunError} |
| tests/ | Utility | Tests (not inspected). | Unknown (missing file contents). | Unknown. | Unknown. | Unknown. | Evidence: Unknown (missing file contents: tests/*.py) |

# Agent-Centric Component Map (if applicable)
Memory:
- Components: RunStore (in-memory dict of GenerateResult).
- State owned: run_id → GenerateResult mapping.
- Invoked by: llmstxt_mcp.generator.safe_generate and server list_runs/read_artifact paths.
- Evidence: src/llmstxt_mcp/runs.py:{RunStore, put_run, list_runs}; Evidence: src/llmstxt_mcp/generator.py:{safe_generate}

Planning:
- Components: Not detected.
- Evidence: Unknown (no planning modules referenced in inspected code)

Evaluation/Reasoning:
- Components: RepositoryAnalyzer using DSPy ChainOfThought signatures for repository and structure analysis.
- State owned: None persisted (DSPy prediction objects only).
- Invoked by: pipeline.run_generation.
- Evidence: src/lmstudiotxt_generator/analyzer.py:{RepositoryAnalyzer, AnalyzeRepository, AnalyzeCodeStructure}; Evidence: src/lmstudiotxt_generator/pipeline.py:{run_generation}

Communication/Adapters:
- Components: GitHub API adapter, LM Studio API/SDK/CLI adapter, MCP FastMCP server, CLI entrypoint, website fetcher.
- State owned: None (stateless adapters).
- Invoked by: pipeline.run_generation (GitHub + LM Studio), full_builder (website fetch), MCP server tools, CLI main.
- Evidence: src/lmstudiotxt_generator/github.py:{gather_repository_material}; Evidence: src/lmstudiotxt_generator/lmstudio.py:{configure_lmstudio_lm}; Evidence: src/llmstxt_mcp/server.py:{mcp, generate}; Evidence: src/lmstudiotxt_generator/cli.py:{main}; Evidence: src/lmstudiotxt_generator/full_builder.py:{_fetch_website}

Tooling/Utilities:
- Components: schema, signatures, hashing, errors, config.
- State owned: Static config/schema data.
- Invoked by: pipeline, MCP server utilities.
- Evidence: src/lmstudiotxt_generator/schema.py:{LLMS_JSON_SCHEMA}; Evidence: src/lmstudiotxt_generator/signatures.py:{AnalyzeRepository}; Evidence: src/llmstxt_mcp/hashing.py:{sha256_file}; Evidence: src/llmstxt_mcp/errors.py:{LMStudioUnavailableError}; Evidence: src/llmstxt_mcp/config.py:{Settings}

# Data & Control Flow
Happy path:
1) External input arrives via CLI or MCP tool.
   Evidence: src/lmstudiotxt_generator/cli.py:{main}; Evidence: src/llmstxt_mcp/server.py:{generate}
2) Orchestrator prepares repo material (file tree, README, package files) from GitHub.
   Evidence: src/lmstudiotxt_generator/pipeline.py:{prepare_repository_material}; Evidence: src/lmstudiotxt_generator/github.py:{gather_repository_material}
3) LM Studio is configured and DSPy analyzer generates llms.txt content.
   Evidence: src/lmstudiotxt_generator/pipeline.py:{run_generation}; Evidence: src/lmstudiotxt_generator/lmstudio.py:{configure_lmstudio_lm}; Evidence: src/lmstudiotxt_generator/analyzer.py:{RepositoryAnalyzer}
4) llms.txt (and optional llms-ctx) is written to output directory.
   Evidence: src/lmstudiotxt_generator/pipeline.py:{_write_text, run_generation}
5) llms-full is assembled by fetching curated links and expanding content.
   Evidence: src/lmstudiotxt_generator/pipeline.py:{run_generation}; Evidence: src/lmstudiotxt_generator/full_builder.py:{build_llms_full_from_repo}
6) Optional fallback JSON is written when LM calls fail; GenerationArtifacts returned.
   Evidence: src/lmstudiotxt_generator/pipeline.py:{run_generation}; Evidence: src/lmstudiotxt_generator/fallback.py:{fallback_llms_payload}
7) MCP layer stores run metadata and serves artifacts by run_id.
   Evidence: src/llmstxt_mcp/generator.py:{safe_generate}; Evidence: src/llmstxt_mcp/runs.py:{RunStore}; Evidence: src/llmstxt_mcp/artifacts.py:{read_resource_text}

Key touchpoints between modules:
- CLI/MCP → pipeline.run_generation (entrypoints)
  Evidence: src/lmstudiotxt_generator/cli.py:{main}; Evidence: src/llmstxt_mcp/generator.py:{safe_generate}
- pipeline → analyzer/github/lmstudio/full_builder/fallback (core orchestration)
  Evidence: src/lmstudiotxt_generator/pipeline.py:{run_generation}
- analyzer → github.construct_github_file_url (link construction)
  Evidence: src/lmstudiotxt_generator/analyzer.py:{build_dynamic_buckets}; Evidence: src/lmstudiotxt_generator/github.py:{construct_github_file_url}

Persistence and side-effect points:
- Filesystem writes: output artifacts (llms.txt, llms-full, llms-ctx, llms.json).
  Evidence: src/lmstudiotxt_generator/pipeline.py:{_write_text, run_generation}; Evidence: src/lmstudiotxt_generator/pipeline.py:{run_generation}
- Network calls: GitHub API, LM Studio API, website fetches.
  Evidence: src/lmstudiotxt_generator/github.py:{fetch_file_tree, fetch_file_content, get_repository_metadata}; Evidence: src/lmstudiotxt_generator/lmstudio.py:{_fetch_models, _load_model_http}; Evidence: src/lmstudiotxt_generator/full_builder.py:{_fetch_website}
- Subprocess: LM Studio CLI load/unload.
  Evidence: src/lmstudiotxt_generator/lmstudio.py:{_load_model_cli, _unload_model_cli}

Dependency edge list:
- cli.py → pipeline.py (CLI delegates generation)
  Evidence: src/lmstudiotxt_generator/cli.py:{main}; Evidence: src/lmstudiotxt_generator/pipeline.py:{run_generation}
- llmstxt_mcp/server.py → llmstxt_mcp/generator.py (tool handler delegates generation)
  Evidence: src/llmstxt_mcp/server.py:{generate}; Evidence: src/llmstxt_mcp/generator.py:{safe_generate}
- llmstxt_mcp/generator.py → lmstudiotxt_generator/pipeline.py
  Evidence: src/llmstxt_mcp/generator.py:{safe_generate}; Evidence: src/lmstudiotxt_generator/pipeline.py:{run_generation}
- pipeline.py → github.py
  Evidence: src/lmstudiotxt_generator/pipeline.py:{prepare_repository_material}; Evidence: src/lmstudiotxt_generator/github.py:{gather_repository_material}
- pipeline.py → lmstudio.py
  Evidence: src/lmstudiotxt_generator/pipeline.py:{run_generation}; Evidence: src/lmstudiotxt_generator/lmstudio.py:{configure_lmstudio_lm}
- pipeline.py → analyzer.py
  Evidence: src/lmstudiotxt_generator/pipeline.py:{run_generation}; Evidence: src/lmstudiotxt_generator/analyzer.py:{RepositoryAnalyzer}
- pipeline.py → full_builder.py
  Evidence: src/lmstudiotxt_generator/pipeline.py:{run_generation}; Evidence: src/lmstudiotxt_generator/full_builder.py:{build_llms_full_from_repo}
- pipeline.py → fallback.py
  Evidence: src/lmstudiotxt_generator/pipeline.py:{run_generation}; Evidence: src/lmstudiotxt_generator/fallback.py:{fallback_llms_payload}
- analyzer.py → github.py (link URL construction)
  Evidence: src/lmstudiotxt_generator/analyzer.py:{build_dynamic_buckets}; Evidence: src/lmstudiotxt_generator/github.py:{construct_github_file_url}
- full_builder.py → github.py (path normalization)
  Evidence: src/lmstudiotxt_generator/full_builder.py:{_resolve_repo_url}; Evidence: src/lmstudiotxt_generator/github.py:{_normalize_repo_path}

# Architecture Assessment
Best-fit archetype: Toolkit with dual entrypoints (CLI + MCP server) for LLM documentation generation.
Justification: Console script entrypoint and MCP FastMCP server wrap a shared pipeline that orchestrates GitHub + LM Studio interactions and filesystem outputs.
Evidence: src/lmstudiotxt_generator/cli.py:{main}; Evidence: src/llmstxt_mcp/server.py:{mcp, main}; Evidence: src/lmstudiotxt_generator/pipeline.py:{run_generation}

Strengths / constraints implied by the architecture:
- Strength: Clear orchestration path and fallback ensures artifacts even on LM failures.
  Evidence: src/lmstudiotxt_generator/pipeline.py:{run_generation}; Evidence: src/lmstudiotxt_generator/fallback.py:{fallback_llms_payload}
- Strength: Supports both API (MCP) and CLI consumers through shared core logic.
  Evidence: src/llmstxt_mcp/generator.py:{safe_generate}; Evidence: src/lmstudiotxt_generator/cli.py:{main}
- Constraint: Network-heavy steps are embedded in analyzer and full builder, reducing separability from I/O.
  Evidence: src/lmstudiotxt_generator/analyzer.py:{_url_alive}; Evidence: src/lmstudiotxt_generator/full_builder.py:{_fetch_website}
- Constraint: Run history is in-memory only; server restarts lose state.
  Evidence: src/llmstxt_mcp/runs.py:{RunStore}
- Constraint: Output directory validation exists but is not enforced in the MCP generation path.
  Evidence: src/llmstxt_mcp/security.py:{validate_output_dir}; Evidence: src/llmstxt_mcp/generator.py:{safe_generate}

Top 5 improvement opportunities:
1) Wire output directory validation into MCP generation.
   Impact: Prevents path traversal or writing outside allowed root when running as MCP server.
   Risk: Low (local change to safe_generate or server tool).
   Scope: Small (add validate_output_dir call before run_generation).
   Evidence: src/llmstxt_mcp/security.py:{validate_output_dir}; Evidence: src/llmstxt_mcp/generator.py:{safe_generate}
2) Decouple URL validation from analyzer content synthesis.
   Impact: Makes llms.txt generation resilient to transient HTTP failures and improves testability.
   Risk: Medium (behavior change; may alter curated buckets).
   Scope: Medium (add validate_urls toggle in pipeline or move URL checks to full_builder).
   Evidence: src/lmstudiotxt_generator/analyzer.py:{build_dynamic_buckets, _url_alive}; Evidence: src/lmstudiotxt_generator/analyzer.py:{RepositoryAnalyzer}
3) Persist MCP run history to disk.
   Impact: Enables artifact retrieval after server restarts and better auditability.
   Risk: Medium (needs migration format and cleanup policy).
   Scope: Medium (swap RunStore backend; serialize GenerateResult).
   Evidence: src/llmstxt_mcp/runs.py:{RunStore}; Evidence: src/llmstxt_mcp/models.py:{GenerateResult}
4) Split full_builder into fetch and render phases.
   Impact: Cleaner boundaries, easier unit testing, and optional offline rendering.
   Risk: Low/Medium (refactor risk, no output changes expected).
   Scope: Medium (extract link fetching and HTML parsing into utilities).
   Evidence: src/lmstudiotxt_generator/full_builder.py:{build_llms_full_from_repo, _fetch_website, _html_to_text}
5) Make artifact types configurable instead of a closed Literal.
   Impact: Easier to add new artifact outputs across CLI and MCP without editing multiple files.
   Risk: Medium (API change; needs coordination across models and readers).
   Scope: Medium (replace ArtifactName Literal and update artifact listing logic).
   Evidence: src/llmstxt_mcp/models.py:{ArtifactName}; Evidence: src/llmstxt_mcp/generator.py:{safe_generate}
