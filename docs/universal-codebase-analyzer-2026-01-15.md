1) **Coverage & Limits**

- Method: Using guidance from `/home/user/.codex/skills/universal-codebase-analyzer/SKILL.md`.
- Observed: repository tree (top-level + src/tests/scripts/artifacts), README, `pyproject.toml`, `package.json`, core generator modules, and MCP server modules. Evidence: `README.md` Overview; `pyproject.toml` `[project]` + `[project.scripts]`; `package.json` scripts; `src/lms_llmsTxt/cli.py`; `src/lms_llmsTxt/pipeline.py`; `src/lms_llmsTxt/analyzer.py`; `src/lms_llmsTxt/full_builder.py`; `src/lms_llmsTxt/github.py`; `src/lms_llmsTxt/lmstudio.py`; `src/lms_llmsTxt_mcp/server.py`; `src/lms_llmsTxt_mcp/generator.py`; `src/lms_llmsTxt_mcp/runs.py`; `src/lms_llmsTxt_mcp/artifacts.py`; `src/lms_llmsTxt_mcp/security.py`.
- Not observed: CI workflows, release scripts behavior, detailed test coverage, and runtime logs; these are **Unknown** until inspecting workflow files, scripts, and test outputs. Evidence gap: no CI config or test output read.
- Not observed: actual LM Studio or GitHub API runtime behavior (network availability, credentials), which affects reliability; **Unknown** until running integration tests or inspecting logs. Evidence gap: no runtime execution captured.

2) **Repository Map (Hierarchical)**

- **lms-llmsTxt (root project)**
  - **Core library: `src/lms_llmsTxt/`**
    - **Type:** Glue/Orchestration + Domain + Infra mix
    - **Purpose (Observed):** Generate `llms.txt` artifacts from GitHub repos, using LM Studio + DSPy, with fallback and full/ctx builders. Evidence: `src/lms_llmsTxt/pipeline.py` `run_generation`; `src/lms_llmsTxt/analyzer.py` `RepositoryAnalyzer`; `src/lms_llmsTxt/full_builder.py` `build_llms_full_from_repo`; `src/lms_llmsTxt/lmstudio.py` LM Studio load/unload helpers.
    - **Public surface (Observed):** CLI entry `lmstxt`. Evidence: `pyproject.toml` `[project.scripts]` `lmstxt = "lms_llmsTxt.cli:main"`; `src/lms_llmsTxt/cli.py` `main`.
    - **Key deps (Observed):** `requests`, `dspy`, `lmstudio`, `pydantic`, `python-dotenv`. Evidence: `pyproject.toml` `dependencies`; `src/lms_llmsTxt/analyzer.py` imports `requests`, `dspy`.
  - **MCP server: `src/lms_llmsTxt_mcp/`**
    - **Type:** Adapter/Service + Glue
    - **Purpose (Observed):** Expose generator as MCP tools; manage run tracking and artifact access. Evidence: `src/lms_llmsTxt_mcp/server.py` `FastMCP` + `@mcp.tool`; `src/lms_llmsTxt_mcp/runs.py` `RunStore`.
    - **Public surface (Observed):** MCP tools `lmstxt_generate_llms_txt`, `lmstxt_generate_llms_full`, `lmstxt_generate_llms_ctx`, `lmstxt_list_runs`, `lmstxt_list_all_artifacts`, `lmstxt_read_artifact` plus resources `lmstxt://runs/...` and `lmstxt://artifacts/...`. Evidence: `src/lms_llmsTxt_mcp/server.py` decorators and resource handlers.
    - **Key deps (Observed):** `mcp.server.fastmcp`, `pydantic_settings`. Evidence: `src/lms_llmsTxt_mcp/server.py` import `FastMCP`; `src/lms_llmsTxt_mcp/config.py` `BaseSettings`.
  - **Tests: `tests/`**
    - **Type:** Quality/Verification
    - **Purpose (Observed):** Pytest coverage for generator and MCP. Evidence: `tests/test_llmstxt_mcp_server.py`, `tests/test_full_builder.py` filenames.
  - **Scripts & artifacts:**
    - **Type:** Utility & Outputs
    - **Purpose (Observed):** codefetch scripts and sample generated artifacts. Evidence: `scripts/codefetch-artifacts.mjs`; `artifacts/**`.

3) **Module Table**

| Unit/Module | Type | Responsibilities | Inputs → Outputs | State owned | Side effects | Extensibility points | Boundary issues | Evidence |
|---|---|---|---|---|---|---|---|---|
| `lms_llmsTxt.cli` | Adapter/Glue | Parse CLI args; call generator; print summary | CLI args → artifact paths summary | None | stdout; invokes generation | CLI flags | CLI tightly bound to `run_generation` | `src/lms_llmsTxt/cli.py` `main`, `build_parser` |
| `lms_llmsTxt.pipeline` | Glue/Orchestration | Orchestrate repo fetch, LM Studio setup, DSPy analysis, fallback, artifact writing | repo_url + config → files on disk + `GenerationArtifacts` | Artifacts under `output_dir` | File writes; network calls via submodules | `build_full`, `build_ctx` flags | Core flow mixes infra + domain | `src/lms_llmsTxt/pipeline.py` `run_generation` |
| `lms_llmsTxt.analyzer` | Domain | DSPy-based analysis and prompt generation | repo material → `llms.txt` content | None | HTTP HEAD/GET for URL validation | TAXONOMY categories | Domain logic depends on HTTP validation | `src/lms_llmsTxt/analyzer.py` `build_dynamic_buckets` |
| `lms_llmsTxt.github` | Infra | GitHub API calls (repo metadata, tree, file contents) | repo_url + token → `RepositoryMaterial` | None | HTTP calls to GitHub API | None | None observed | `src/lms_llmsTxt/github.py` `gather_repository_material` |
| `lms_llmsTxt.full_builder` | Utility/Adapter | Build `llms-full.txt` by resolving links and fetching content | curated text + links → aggregated text | None | HTTP calls to GitHub/raw/website | Link resolution strategy | Duplicate URL resolution logic vs other modules | `src/lms_llmsTxt/full_builder.py` `_resolve_repo_url`, `_extract_links` |
| `lms_llmsTxt.lmstudio` | Infra | Probe/load/unload LM Studio models via HTTP/CLI/SDK | config → LM Studio availability | None | HTTP requests; subprocess `lms` | Multiple endpoint patterns | Complex endpoint logic embedded in module | `src/lms_llmsTxt/lmstudio.py` `_fetch_models`, `_load_model_http` |
| `lms_llmsTxt_mcp.server` | Adapter/Service | MCP tool and resource endpoints, background jobs | MCP requests → run records/resources | RunStore (in-memory) | Threads; file reads; stdout JSON-RPC | MCP tool suite | Artifact path logic duplicated with generator | `src/lms_llmsTxt_mcp/server.py` `@mcp.tool`, `RunStore` |
| `lms_llmsTxt_mcp.runs` | Utility | In-memory run tracking with TTL/limit cleanup | run_id + updates → RunRecord | `_runs` dict | Background cleanup thread | TTL/max settings | No persistence across restarts | `src/lms_llmsTxt_mcp/runs.py` `RunStore` |

4) **Dependency Edge List**

- `lms_llmsTxt.cli` → `lms_llmsTxt.pipeline`: CLI calls `run_generation`. Evidence: `src/lms_llmsTxt/cli.py` `run_generation`.
- `lms_llmsTxt.pipeline` → `lms_llmsTxt.github`: Fetch repo materials before analysis. Evidence: `src/lms_llmsTxt/pipeline.py` `prepare_repository_material`; `src/lms_llmsTxt/github.py` `gather_repository_material`.
- `lms_llmsTxt.pipeline` → `lms_llmsTxt.analyzer`: DSPy analysis produces `llms.txt`. Evidence: `src/lms_llmsTxt/pipeline.py` `RepositoryAnalyzer` call.
- `lms_llmsTxt.pipeline` → `lms_llmsTxt.lmstudio`: Configure and unload model. Evidence: `src/lms_llmsTxt/pipeline.py` `configure_lmstudio_lm` and `unload_lmstudio_model`.
- `lms_llmsTxt.pipeline` → `lms_llmsTxt.full_builder`: Build `llms-full.txt`. Evidence: `src/lms_llmsTxt/pipeline.py` `build_llms_full_from_repo`.
- `lms_llmsTxt_mcp.server` → `lms_llmsTxt_mcp.generator`: MCP tools spawn background safe generation. Evidence: `src/lms_llmsTxt_mcp/server.py` `_spawn_background` with `safe_generate_llms_txt`.
- `lms_llmsTxt_mcp.generator` → `lms_llmsTxt.pipeline`: Uses core generator for llms.txt. Evidence: `src/lms_llmsTxt_mcp/generator.py` `run_generation`.
- `lms_llmsTxt_mcp.server` → `lms_llmsTxt_mcp.runs`: Tracks run status. Evidence: `src/lms_llmsTxt_mcp/server.py` `RunStore`.
- `lms_llmsTxt_mcp.server` → `lms_llmsTxt_mcp.artifacts`: Read artifacts and list resources. Evidence: `src/lms_llmsTxt_mcp/server.py` `read_artifact_chunk`, `scan_artifacts`.

5) **Data & Control Flow Narratives**

- **CLI generation (Observed):** `lmstxt` CLI parses args → builds `AppConfig` → `run_generation` → fetch repo metadata/tree/readme/package files → configure LM Studio model → DSPy analyzer returns `llms.txt` or fallback → write `llms.txt` plus optional `llms-ctx.txt` → build `llms-full.txt` → write JSON if fallback. Evidence: `src/lms_llmsTxt/cli.py` `main`; `src/lms_llmsTxt/pipeline.py` `run_generation`; `src/lms_llmsTxt/github.py` `gather_repository_material`.
- **Fallback path (Observed):** LM Studio/DSPy failure triggers `fallback_llms_payload` → `fallback_markdown_from_payload` → JSON written to disk. Evidence: `src/lms_llmsTxt/pipeline.py` exception handling around `RepositoryAnalyzer` and `fallback_llms_payload`.
- **MCP tool generation (Observed):** `lmstxt_generate_llms_txt` → validate output dir → create RunRecord → spawn background `safe_generate_llms_txt` → call `run_generation` with `build_full=False` → update run artifacts with sha256 hashes. Evidence: `src/lms_llmsTxt_mcp/server.py` `generate_llms_txt`; `src/lms_llmsTxt_mcp/generator.py` `safe_generate_llms_txt`.
- **MCP artifact read (Observed):** `lmstxt_read_artifact` → resolve run or file path → read chunk and return JSON payload. Evidence: `src/lms_llmsTxt_mcp/server.py` `read_artifact`; `src/lms_llmsTxt_mcp/artifacts.py` `read_artifact_chunk`.

6) **Boundary Problems & Refactor Candidates**

- **Duplicate artifact path derivation (Observed):** `_artifact_path_from_url` exists in both server and generator with similar suffix maps, risking divergence. Impact: inconsistent artifact paths across MCP tools. Scope: small refactor to a shared utility. Evidence: `src/lms_llmsTxt_mcp/server.py` `_artifact_path_from_url`; `src/lms_llmsTxt_mcp/generator.py` `_artifact_path_from_url`.
- **Run history is memory-only (Observed):** `RunStore` uses in-memory dict with TTL cleanup; no persistence across restarts. Impact: clients lose run status/history after server restart. Scope: add persistence adapter or optional disk-backed store. Evidence: `src/lms_llmsTxt_mcp/runs.py` `_runs` dict and cleanup thread.
- **Orchestration mixes infra and domain (Observed):** `run_generation` coordinates network calls, LM setup, fallback logic, and file writes in one function. Impact: higher coupling and harder unit isolation. Scope: extract interfaces for GitHub/LM Studio and artifact writing. Evidence: `src/lms_llmsTxt/pipeline.py` `run_generation` calling `gather_repository_material`, `configure_lmstudio_lm`, `_write_text`.
- **URL validation logic tied to domain analyzer (Observed):** `build_dynamic_buckets` validates URLs via HTTP in analyzer module. Impact: domain output depends on network availability; harder to test offline. Scope: inject validator or make validation optional at call site. Evidence: `src/lms_llmsTxt/analyzer.py` `_url_alive`, `_github_path_exists` usage.

7) **System Archetype & Naming**

- **Archetype (Observed):** A CLI-first generator with a companion MCP server exposing async tool endpoints. Evidence: `pyproject.toml` scripts `lmstxt` and `lmstxt-mcp`; `src/lms_llmsTxt_mcp/server.py` `FastMCP` server.
- **Analogies (Inferred):** Similar to a static doc generator plus API wrapper (CLI pipeline + MCP service facade). Evidence: `src/lms_llmsTxt/pipeline.py` artifact writing and `src/lms_llmsTxt_mcp/server.py` tool/resource exposure.
- References consulted: No external references consulted.
