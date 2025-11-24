# path: ui/AGENTS.md

# AGENTS.md for `ui`

## Hierarchical Policy

- Inherits system-wide conventions from `.ruler/AGENTS.md` and repo-level rules from `../AGENTS.md`.
- Narrows scope to all user-facing interface code under `ui/`.
- Treats the Python backend in `src/lmstudiotxt_generator` as a remote service; UI never reaches into backend internals directly.
- Child directories under `ui/` may add their own `AGENTS.md` files (for `components/`, `views/`, etc.) to further specialize patterns without breaking these constraints.

## Domain Vocabulary

- View: A screen or page-level component responsible for composing layout and wiring data + actions (e.g., “Generate llms.txt for repo”, “Browse artifacts”).
- Component: Reusable, mostly presentation-focused building blocks (buttons, forms, lists, cards) that receive state and callbacks via props.
- Data client: Small module responsible for calling backend interfaces (HTTP, RPC, CLI bridge) and returning typed results to the UI (e.g., `getRepoSummary`, `triggerGenerationJob`).
- UI state:
  - Local state: Component-level state for form inputs, toggles, and ephemeral view concerns.
  - Remote state: Backend-derived data (generation status, artifact metadata) fetched via data clients and cached by the chosen data-fetching library.
- Navigation: Any routing mechanism (SPA router, Next-style routes, etc.) that switches between views.

## Allowed Patterns

- Directory responsibilities:
  - Keep reusable UI components in subdirectories such as `ui/components`, `ui/widgets`, or similar.
  - Keep page or screen-level views in `ui/views`, `ui/pages`, or framework-specific route folders.
  - Keep backend integration logic in a dedicated place such as `ui/api`, `ui/data`, or `ui/lib/api`.
- Data access:
  - All communication with the backend goes through data client modules that:
    - Encapsulate endpoint URLs or CLI invocation details.
    - Perform input validation and minimal response shaping.
    - Return typed objects or discriminated unions representing success/error states.
  - Views and components call data clients, not `fetch`, `axios`, or other low-level transport APIs directly, except in the data client layer itself.
- State management:
  - Use view-local state for ephemeral UI concerns (input values, open/closed panels, selected tabs).
  - Use a query/cache layer (or equivalent abstraction) in data clients or hooks for backend data; prefer declarative patterns (`useXxxQuery`, `useXxxMutation`) over manual promise wiring.
- Error and loading handling:
  - Centralize generic loading and error UI components (spinners, banners, toasts) and re-use them across views.
  - Data clients surface structured error information (status code, message, category) for consistent error rendering.
- Cross-boundary usage:
  - UI may depend on generated or hand-written TypeScript types that describe backend contracts (e.g., DTOs derived from llms.txt metadata) but not on Python classes themselves.
  - It is acceptable to introduce a thin shim that translates backend JSON payloads into strongly-typed UI models.

## Prohibited Patterns

- Backend coupling:
  - Do not import backend Python modules, Python-generated files, or use language-bridging tricks from `ui/`.
  - Do not reconstruct backend logic in the UI (e.g., reimplementing DSPy flows, llms.txt generation rules, or GitHub crawling inside the frontend).
- Data fetching and side effects:
  - Do not perform ad-hoc `fetch`/HTTP calls directly in random components or views; all network calls must go through data clients.
  - Do not trigger side-effectful operations (file writes, subprocess calls, LM Studio requests) directly from UI code; the backend remains the only owner of those side effects.
- Global state misuse:
  - Do not store entire backend responses or large artifact payloads in global state if a query/cache layer already manages them; keep global state limited to cross-view UI concerns (theme, layout, session identity).
  - Do not use global state or mutable singletons to coordinate backend calls; use explicit functions/hooks instead.
- Security and secrets:
  - Do not embed backend credentials, tokens, or secret URLs into UI code; all secrets belong in backend or infrastructure configuration.
  - Do not allow UI to construct arbitrary backend target URLs from user input without sanitization and explicit intent.

## Boundaries

- Inbound boundaries:
  - Human users and test harnesses interact with this directory via:
    - Application shell (root UI entrypoint / router).
    - Storybook or component preview setups (if present) that live under `ui/` or a sibling tooling directory.
- Outbound boundaries:
  - UI talks only to:
    - The backend’s exposed interfaces (HTTP endpoints, RPC layer, or CLI bridge) via data clients.
    - Browser APIs or framework-provided utilities that are safe on the client.
  - UI must not talk directly to external services that the backend already owns (GitHub, LM Studio, arbitrary websites); those calls belong in the backend integration layer.
- Interaction with other bounded contexts:
  - When adding new flows that need backend work, first ensure the backend exposes a stable, documented interface; then add or update data clients under `ui/` to consume it.
  - Do not introduce cross-dependencies from backend code into `ui/`; any shared types or contracts must be transported via generated schemas or manually curated type definitions in the UI.
