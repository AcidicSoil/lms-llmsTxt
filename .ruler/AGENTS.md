# AGENTS.md

Centralised AI agent instructions. Add coding guidelines, style guides, and project context here.

Ruler concatenates all .md files in this directory (and subdirectories), starting with AGENTS.md (if present), then remaining files in sorted order.

## Hierarchical Policy

- Inherits system-wide conventions from `.ruler/AGENTS.md`.
- Defines project-wide architecture, directory ownership, and cross-boundary interaction rules.
- Delegates detailed behavioral rules to nested `AGENTS.md` files:
  - `src/lmstudiotxt_generator/AGENTS.md` for the Python DSPy + LM Studio backend.
  - `ui/AGENTS.md` for any interactive UI or dashboard.
- For any task touching a specific area, read the most specific `AGENTS.md` for that directory after this file.

## Domain Vocabulary

- Backend: Python package under `src/lmstudiotxt_generator` that owns all llms.txt generation, DSPy programs, and LM Studio connectivity.
- UI: Any web or desktop user interface living under `ui/` that triggers backend operations and visualizes results.
- Artifacts: Generated llms-related files (e.g., `*-llms.txt`, `*-llms-full.txt`, `*-llms-ctx.txt`, `*-llms.json`) written under an `OUTPUT_DIR` (default `./artifacts/`).
- Orchestration: High-level flows that wire inputs (GitHub repo URL, config) to backend calls and artifact emission (CLI entrypoints, job runners, CI scripts).
- Integration: Code that talks to external systems (GitHub, LM Studio, web APIs, file system) but does not own business rules.

## Allowed Patterns

- Directory ownership:
  - Keep Python source under `src/lmstudiotxt_generator/`.
  - Keep any UI implementation under `ui/`.
  - Keep packaging, configuration, and repo-level tooling at the root (e.g., `pyproject.toml`, `README.md`, `.env`, CI config).
- Architectural layering:
  - Root-level scripts and tooling may orchestrate work but must not implement domain logic; they call into backend public APIs or invoke CLI entrypoints.
  - Backend owns all llms.txt generation logic, DSPy programs, GitHub integration, and LM Studio integration.
  - UI owns all presentation logic, user workflows, and client-side state; it treats the backend as a black-box service.
- Public surfaces:
  - Prefer using the backend’s documented public APIs (e.g., `lmstudio-llmstxt` CLI, or a dedicated Python entrypoint) rather than importing deep internal modules from root-level tools.
  - When adding new top-level tools (CLI wrappers, scripts, CI jobs), route through the same backend entrypoints used by the official CLI or server code.
- Policy propagation:
  - When creating a new top-level directory that contains runtime code (e.g., `server/`, `workers/`), add an `AGENTS.md` in that directory and explicitly define its relationship to backend and UI.
  - Use nested `AGENTS.md` files to tighten, not loosen, constraints defined here or in `.ruler/AGENTS.md`.

## Prohibited Patterns

- Cross-boundary violations:
  - UI code (under `ui/`) must not import Python modules directly or depend on internal backend file paths; communication must go through a stable interface (HTTP API, CLI wrapper, message bus, etc.).
  - Backend Python code must not assume knowledge of UI framework internals, UI routing, or client-side state structures.
- Root-level logic:
  - Do not put business logic, DSPy programs, or LM Studio/GitHub integration code directly in root-level scripts or modules.
  - Do not introduce new long-lived runtime modules at the repo root without a corresponding `AGENTS.md` that defines their scope and dependencies.
- Environment handling:
  - Do not read environment variables directly from scattered modules; centralize environment configuration in dedicated config modules (e.g., backend `AppConfig`) and pass configuration objects downward.
- Tooling:
  - Do not create tooling that bypasses backend validation or error handling (e.g., scripts that call GitHub APIs independently of the backend integration layer).

## Boundaries

- Inbound boundaries (how the repo is used):
  - Human operators and CI entrypoints interact with the project via:
    - CLI commands (e.g., a console script that calls backend orchestration functions).
    - Optional HTTP or job runner surfaces if/when they are introduced in separate bounded contexts.
- Outbound boundaries (what the repo talks to):
  - External services (GitHub, LM Studio, websites) are only accessed by the backend integration layer, not by root-level scripts or the UI.
  - Roots scripts may perform basic file system operations (e.g., managing `artifacts/`, reading configuration) but must not duplicate backend logic.
- Delegation map:
  - For backend changes, follow `src/lmstudiotxt_generator/AGENTS.md`.
  - For UI changes, follow `ui/AGENTS.md`.
  - For new cross-cutting areas (e.g., `server/`, `infra/`, `workers/`), introduce a local `AGENTS.md` and explicitly document dependencies on backend and UI.
