# path: src/lmstudiotxt_generator/AGENTS.md

# AGENTS.md for `src/lmstudiotxt_generator`

## Hierarchical Policy

- Inherits system-wide conventions from `.ruler/AGENTS.md`: keep business logic and state computation in pure code; concentrate side effects (I/O, networking, environment) at explicit boundaries; treat “effects” as boundary concerns, not as general control flow. :contentReference[oaicite:0]{index=0}
- Interprets “server-synced domain data vs ephemeral UI/session state” as:
  - Domain data = repository metadata, file trees, documentation content, DSPy program outputs, and generated `llms.txt` artifacts.
  - Ephemeral state = CLI arguments, environment-derived configuration, transient LM caches. Persist only domain data. :contentReference[oaicite:1]{index=1}
- Mirrors the “loader/server function” pattern as: CLI and library callers invoke `run_generation` as the only public orchestration entrypoint; all external I/O (GitHub APIs, LM Studio APIs, HTTP scraping, filesystem writes) happens inside orchestrator and integration modules, not in core data models or DSPy signatures.
- Applies DSPy’s “programming, not prompting” principle: encode behavior as typed `dspy.Signature` and `dspy.Module` graphs; avoid ad-hoc prompt strings scattered across the codebase; any future optimization uses DSPy optimizers rather than manual prompt tweaking.
- Treats LM calls like RPC: one narrow LM access layer (`lmstudio.py` via `configure_lmstudio_lm`) configures the global `dspy.LM`; all DSPy modules depend on that configuration and never manage HTTP or API keys directly.

## Domain Vocabulary

- RepositoryMaterial: aggregate of inputs fetched from GitHub for a repository (URL, file tree, README, package metadata, default branch, privacy flag) used as the canonical “domain snapshot” for generation.
- GenerationArtifacts: set of paths to generated artifacts (`*-llms.txt`, `*-llms-full.txt`, optional `*-llms-ctx.txt`, and fallback JSON), plus a flag indicating whether the fallback path was used.
- `llms.txt`: curated Markdown index of project documentation and key resources, designed for LLMs to quickly locate relevant pages (title, short summary, sections of links).
- `llms-full.txt`: expanded companion document that inlines the full content of relevant docs and source snippets into a single, large text file to be passed as context to LLMs.
- `llms-ctx.txt`: compact context file derived from `llms.txt` for tooling that expects a distilled prompt context. (Generated only when `llms_txt.create_ctx` is available at runtime.)
- DSPy Signature: a declarative, typed interface describing inputs/outputs and documentation for LM calls (e.g., `AnalyzeRepository`, `AnalyzeCodeStructure`, `GenerateUsageExamples`, `GenerateLLMsTxt`). Signatures define the “API surface” of the DSPy program.
- DSPy Module (`RepositoryAnalyzer`): compositional LM pipeline wiring signatures together via `dspy.ChainOfThought`, producing structured predictions (analysis, structure, rendered markdown). This is the main “program” optimized or extended in future DSPy work.
- LM Studio connectivity: the responsibility of `lmstudio.py`—probing endpoints, loading/unloading models, configuring DSPy’s LM wrapper around LM Studio’s OpenAI-compatible API.
- Fallback path: heuristic generator using `fallback_llms_payload` and `fallback_markdown_from_payload` when DSPy/LM calls fail; its JSON output conforms to `LLMS_JSON_SCHEMA` to keep `llms.txt` format stable.

## Allowed Patterns

- Directory-level architecture:
  - `cli.py` is the only entrypoint for the console; it parses arguments, builds `AppConfig`, and calls `run_generation`.
  - `pipeline.py` is the only place that orchestrates GitHub access, DSPy runs, fallback logic, and artifact writing.
  - Integration modules (`github.py`, `full_builder.py`, `lmstudio.py`) encapsulate all HTTP and external service details.
  - Core domain modules (`models.py`, `schema.py`, `signatures.py`, `analyzer.py`, `fallback.py`) remain free of CLI/argparse and OS-level plumbing.
- DSPy usage:
  - Define all LM interactions via `dspy.Signature` and `dspy.Module`, with rich field descriptions and docstrings instead of inline prompt strings.
  - Use `dspy.LM` configured in `configure_lmstudio_lm` as the only LM backend for this package; any new LM backend must live in a parallel adapter module, not scattered calls.
  - When adding training/optimization flows, use DSPy optimizers (e.g., SIMBA or BootstrapFewShot) in separate “training” modules that compile `RepositoryAnalyzer` or successor programs against curated datasets and metrics.
- llms.txt generation:
  - Build structure via `RepositoryAnalyzer` first, then render with `render_llms_markdown`, and only then write files; treat `llms.txt` content as pure data until the final write.
  - Use `build_dynamic_buckets` and taxonomy scoring to derive link sections from the GitHub file tree and raw URLs; customizations should extend taxonomy and scoring helpers rather than reimplementing classification logic.
  - For fallback behavior, construct a JSON payload with `fallback_llms_payload` and derive Markdown via `fallback_markdown_from_payload`, preserving the schema contract for downstream tools.
- Configuration and environment:
  - Centralize environment access in `AppConfig`; anywhere else should consume an `AppConfig` instance, not read env vars directly. :contentReference[oaicite:23]{index=23}
  - Use `AppConfig.ensure_output_root(owner, repo)` to compute output directories and create them, rather than ad-hoc path concatenation.
- External services:
  - Access GitHub APIs only through `github.py` functions (`owner_repo_from_url`, `get_default_branch`, `fetch_file_tree`, `fetch_file_content`, `gather_repository_material`, `construct_raw_url`).
  - Access GitHub raw content and build `llms-full.txt` only through `full_builder.py` helpers (`parse_github_link`, `gh_get_file`, `fetch_raw_file`, etc.).
  - Access LM Studio (HTTP, SDK, CLI) only via `lmstudio.py` helpers; configure DSPy globally via `configure_lmstudio_lm` before running any DSPy module.
- Error handling and fallbacks:
  - In `run_generation`, catch LM-related errors (LiteLLM exceptions, connectivity issues) and fall back to heuristic generation; always set `used_fallback` in `GenerationArtifacts` when the fallback path is taken.
  - Log warnings on LM failures and fallback activation but never crash the CLI with a raw stack trace for expected external failures (e.g., rate limits, auth errors).
- Caching and performance:
  - Prefer DSPy’s LM caching for repeated experiments (`cache_lm` flag) instead of custom in-memory caches in this package.
  - For HTTP calls, reuse the module-level `requests.Session` instances where provided instead of creating new sessions per call.

## Prohibited Patterns

- DSPy and prompts:
  - No ad-hoc prompt engineering outside DSPy Signatures and Modules; do not construct LM prompts as free-form strings in pipeline, CLI, or integration modules. All instructions belong in signature docstrings and field descriptions.
  - Do not call OpenAI-style HTTP endpoints or other LM APIs directly; use `dspy.LM` created in `configure_lmstudio_lm` as the single abstraction.
- Side effects and I/O:
  - No filesystem writes from DSPy modules (`RepositoryAnalyzer`) or from pure helpers like `render_llms_markdown`; only `pipeline.py` (and future orchestration modules) may write `llms.txt` artifacts.
  - No network calls from data model or schema modules (`models.py`, `schema.py`, `signatures.py`); networking is restricted to `github.py`, `full_builder.py`, `lmstudio.py`, and the limited link validation helpers in `analyzer.py`.
  - No subprocess usage outside `lmstudio.py` (where LM Studio CLI integration is explicitly handled).
- Configuration and global state:
  - Do not read environment variables outside `config.py` except in test code; pass configuration via `AppConfig`.
  - No module-level mutable globals for caching, metrics, or configuration; rely on LM caching, function parameters, or explicit cache objects instead.
- CLI and user interaction:
  - No interactive prompts (`input`, `getpass`, etc.) in this package; CLI must be fully configurable via flags and environment. :contentReference[oaicite:40]{index=40}
  - Do not import `argparse` or `sys` outside `cli.py`. :contentReference[oaicite:41]{index=41}
- Architecture and coupling:
  - `cli.py` must not import or depend directly on integration modules like `github.py`, `full_builder.py`, or `lmstudio.py`; it talks only to `config.py` and `pipeline.py`.
  - `analyzer.py` must not depend on CLI or configuration modules; it is a pure DSPy program plus lightweight URL validation.
  - `fallback.py` must not perform HTTP requests or filesystem I/O; it operates only on data already fetched. :contentReference[oaicite:44]{index=44}
- llms.txt format:
  - Do not change the top-level structure of `llms.txt`/`llms-full.txt` (title, short description, sections with link lists) without updating `LLMS_JSON_SCHEMA` and the downstream tooling that consumes it.

## Boundaries

- Inbound boundaries:
  - CLI boundary: `cli.py:main` is the only approved console entrypoint; it must be wired in `pyproject.toml` or equivalent console_scripts, and only call `build_parser` + `run_generation`.
  - Library boundary: external Python callers may only use the public API exposed in `__init__.py` (`RepositoryAnalyzer`, `AppConfig`, `GenerationArtifacts`, `RepositoryMaterial`, LM Studio helpers, schema) and `run_generation`. Internal modules are not part of the stable public surface.
- Outbound boundaries:
  - GitHub: all GitHub REST and raw-content calls are limited to `github.py` and `full_builder.py`; changing token handling, rate-limit behavior, or URL construction must occur there.
  - LM Studio: all HTTP, SDK, and CLI interactions with LM Studio are limited to `lmstudio.py`; other modules must treat LM Studio as an abstract LM provided by DSPy.
  - Web documentation: lightweight HEAD/GET probes for link validation are allowed only via the helpers in `analyzer.py` that use `_URL_SESSION`.
  - Filesystem: artifact writing (`*-llms.txt`, `*-llms-full.txt`, `*-llms-ctx.txt`, `*-llms.json`) is restricted to `pipeline.py`, using paths derived from `AppConfig.ensure_output_root`.
- Allowed import graph (enforced directionally):
  - `cli.py` → `config.py`, `pipeline.py`
  - `pipeline.py` → `analyzer.py`, `config.py`, `fallback.py`, `github.py`, `lmstudio.py`, `models.py`, `schema.py`, `full_builder.py`
  - `analyzer.py` → `github.py`, `signatures.py`, `dspy`
  - `fallback.py` → `analyzer.py`, `schema.py`
  - `github.py` → `models.py`
  - `full_builder.py` → `requests` only (no internal imports beyond simple types/constants)
  - `lmstudio.py` → `config.py`, `dspy`
  - `schema.py` and `models.py` → standard library only (pure data definitions)
- Cross-cutting rule: new modules must declare which layer they belong to (core/domain, integration, orchestration, or entrypoint) and may only depend inward (toward core/domain), never outward (core → integration, domain → CLI).
