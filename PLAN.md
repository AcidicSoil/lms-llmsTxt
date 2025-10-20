**Goal**
- Ensure `llms-full` builds use public-friendly fetching by default, eliminating GitHub 403s.

**User Story**
- As a CLI maintainer, I need the generator to pick the correct GitHub fetch strategy so public
  repos build cleanly while private repos still work with tokens.

**Milestones**
- Milestone 1: Map current orchestration and data flow between `pipeline.py` and `full_builder.py`.
- Milestone 2: Introduce repo visibility checks and switch fetching based on public/private status.
- Milestone 3: Harden error messaging and tests covering both fetch strategies.

**Tasks**
- [x] Document current GitHub fetch entry points and data passed into `build_llms_full_from_repo`
  (Owner: Codex, Est: 1h, Files: src/lmstudiotxt_generator/pipeline.py).
  - Acceptance: Notes clarify when authenticated vs raw URLs are used today.
  - Notes: `pipeline.prepare_repository_material` fetches via authenticated API and hands markdown
    links into `build_llms_full_from_repo`, which always re-fetches each curated URL via GitHub API.
- [x] Add a repo visibility helper in `github.py` and thread the signal through the pipeline to the
  llms-full builder (Owner: Codex, Est: 3h, Files: src/lmstudiotxt_generator/github.py).
  - Acceptance: Public repos skip authenticated fetches; private repos still call GitHub API.
  - Notes: `get_repository_metadata` now surfaces `default_branch` and `is_private` for downstream use.
- [x] Refactor `build_llms_full_from_repo` to branch on fetch strategy and support raw URL pulls
  (Owner: Codex, Est: 3h, Files: src/lmstudiotxt_generator/full_builder.py).
  - Acceptance: Public repos resolve curated links without `[fetch-error]` markers.
  - Notes: `prefer_raw=True` routes curated links through `fetch_raw_file` without token usage.
- [x] Enhance authenticated fetch error handling to highlight token scope/expiry issues
  (Owner: Codex, Est: 1h, Files: src/lmstudiotxt_generator/full_builder.py).
  - Acceptance: 403 paths include actionable token guidance in the emitted block.
  - Notes: `_format_http_error` appends repo-scope guidance for GitHub 403 responses.
- [x] Add unit coverage for both public and private fetch paths plus 403 messaging
  (Owner: Codex, Est: 2h, Files: tests/test_full_builder.py).
  - Acceptance: New tests fail on regressions and pass after implementation.
  - Notes: Added coverage for raw fetch success, private API path, and 403 guidance output.

**Won't do**
- Rewrite the CLI interface or argument parsing logic.
- Add caching layers or persistence beyond current artifact output.

**Ideas for later**
- Offer a `--force-auth` flag to override auto-detected fetch strategy.
- Cache repository visibility lookups to avoid repeated API calls.

**Validation**
- Run `python3 -m pytest`; currently blocked because pytest is not installed in the environment.
- Manual smoke test: invoke CLI against a public repo with an invalid token to confirm fallback.

**Risks**
- GitHub rate limits may impact visibility checks; mitigate with reuse of existing session headers.
- Private repo detection may misbehave if credentials are missing; ensure clear exceptions guide fix.
- Raw URL fetches can drift with default branch changes; keep branch discovery logic consistent.
