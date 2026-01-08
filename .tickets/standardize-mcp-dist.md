Parent Ticket:

* Title:

  * Standardize `lms-llmsTxt` MCP distribution/run story (pipx/uvx), client configs, and artifacts root handling
* Summary:

  * Make the Python FastMCP stdio server “just work” across MCP clients without `npx` by standardizing install/run guidance (pipx/uv tool), executable naming, copy/paste client configs (including Windows/WSL clarity), and an easy/safe artifacts-root strategy.
* Source:

  * Link/ID: Not provided
  * Original ticket excerpt (≤25 words) capturing the overall theme:

    * “publish… and ship consistent, copy/pasteable configs + a clearer artifacts-root strategy”
* Global Constraints:

  * Do not rely on `npx` as the primary distribution/run path.
  * Do not store artifacts “wherever the package is installed”.
  * Keep the allowed-root boundary concept (`LLMSTXT_MCP_ALLOWED_ROOT`; `output_dir` must be within it).
  * Out of scope:

    * “Publishing a true npm wrapper (`npx ...`)”
    * “Porting the MCP server to TypeScript”
    * “Remote MCP transport (Streamable HTTP) implementation”
* Global Environment:

  * MCP server: Python FastMCP stdio server
  * Clients: Claude Desktop, Cursor, OpenAI Codex CLI (`~/.codex/config.toml`), LM Studio (Windows)
  * OS: Windows + WSL mixed setup (LM Studio on Windows; server installed in WSL in at least one scenario)
  * Repo: `AcidicSoil/lms-llmsTxt`
* Global Evidence:

  * Conversation transcript: `MCP callable options via npx.md`
  * Referenced variables/options: `LLMSTXT_MCP_ALLOWED_ROOT`, `OUTPUT_DIR`, `ENABLE_CTX`, `LMSTUDIO_BASE_URL`, `GITHUB_ACCESS_TOKEN` (placeholders)
  * Tools/resources: `lmstxt_generate_llms_txt`, `lmstxt_list_all_artifacts`, `lmstxt_read_artifact`, `lmstxt://artifacts/...`
  * Screenshots referenced for LM Studio/Codex config issues (error text not captured)

Split Plan:

* Coverage Map:

  * Original item: “users want to ‘just work’ across MCP clients… without relying on `npx`”

    * Assigned Ticket ID: T2
  * Original item: Confusion: “how to run/install… (pipx/uvx vs npx)”

    * Assigned Ticket ID: T2
  * Original item: Confusion: “inconsistent executable naming… (`lmstxt-mcp` vs `llmstxt-mcp`)”

    * Assigned Ticket ID: T1
  * Original item: Confusion: “Windows vs WSL process spawning for LM Studio”

    * Assigned Ticket ID: T3
  * Original item: Confusion: “how users point the server at an existing `artifacts/` directory safely”

    * Assigned Ticket ID: T4
  * Original item: Goal: “publish the renamed PyPI project (tags ready)… consistent… configs + clearer artifacts-root strategy”

    * Assigned Ticket ID: T6
  * Original item: Background: “Python FastMCP server (stdio)… launched by MCP clients via local process command”

    * Assigned Ticket ID: Info-only
  * Original item: Background: “user initially asked… `npx`… then selected… pipx/uvx… docs”

    * Assigned Ticket ID: Info-only
  * Original item: Background: “renamed… `pyproject.toml`… remote main… PyPI project… ready for pushing tags”

    * Assigned Ticket ID: T6
  * Original item: Background: “LM Studio… on Windows… spawns… Windows/WSL… friction”

    * Assigned Ticket ID: T3
  * Original item: Current behavior: confusion about “no-install” vs “install once” and why `npx` common but not applicable

    * Assigned Ticket ID: T2
  * Original item: Current behavior: “Executable naming appears inconsistent… package name differs… (`pipx run --spec ... <exe>` / `uvx --from ... <exe>` patterns)”

    * Assigned Ticket ID: T1
  * Original item: Current behavior: “LM Studio configuration on Windows… MCP JSON malformed (`env` array)… Unix-style paths… WSL-only install… failures”

    * Assigned Ticket ID: T3
  * Original item: Current behavior: “Artifacts… allowed-root… `OutputDirNotAllowedError`… UX for existing artifacts dir not clear”

    * Assigned Ticket ID: T4
  * Original item: Expected: “single, stable ‘install once’ recommendation… pipx/uv tool install… stable executable”

    * Assigned Ticket ID: T2
  * Original item: Expected: “Optional ‘try without installing’… `pipx run` / `uvx`… not primary”

    * Assigned Ticket ID: T2
  * Original item: Expected: “Artifacts handling… default stable location or point to existing dir… not ephemeral install dirs”

    * Assigned Ticket ID: T4
  * Original item: Expected: “Cross-platform guidance explicit… Windows clients require Windows-runnable commands; WSL installs won’t be visible”

    * Assigned Ticket ID: T3
  * Original item: Requirement: “Ensure canonical MCP executable name is consistent everywhere… pick one and align”

    * Assigned Ticket ID: T1
  * Original item: Requirement: “Ensure MCP server dependencies are not only available via dev extras”

    * Assigned Ticket ID: T1
  * Original item: Requirement: README “recommended” install/run using `pipx install` and/or `uv tool install`

    * Assigned Ticket ID: T2
  * Original item: Requirement: README optional “no-install” snippets (`pipx run --spec …`, `uvx --from …`)

    * Assigned Ticket ID: T2
  * Original item: Requirement: Provide canonical configs: Claude Desktop, Cursor, Codex `config.toml`, LM Studio (Windows)

    * Assigned Ticket ID: T3
  * Original item: Requirement: “Document use of `cwd`… stabilize relative paths”

    * Assigned Ticket ID: T2
  * Original item: Requirement: “Keep allowed-root boundary… document clearly”

    * Assigned Ticket ID: T4
  * Original item: Requirement: “Document ‘serve an existing artifacts directory’… expected structure `<root>/<owner>/<repo>/...`”

    * Assigned Ticket ID: T4
  * Original item: Requirement: “Do not store artifacts ‘wherever the package is installed’”

    * Assigned Ticket ID: T4
  * Original item: Consider improvements: “Support MCP ‘Roots’ (`roots/list`)…”

    * Assigned Ticket ID: T5
  * Original item: Consider improvements: “Fallback to a stable OS user-data directory when Roots unavailable”

    * Assigned Ticket ID: T5
  * Original item: Consider improvements: “Add a tool that returns resolved paths…”

    * Assigned Ticket ID: T5
  * Original item: Release readiness: “Pre-tag validation… smoke test… if versioning tag-derived… pushing first tag required”

    * Assigned Ticket ID: T6
  * Original item: Out of scope: “Publishing a true npm wrapper (`npx ...`)…”

    * Assigned Ticket ID: Info-only
  * Original item: Out of scope: “Porting… to TypeScript…”

    * Assigned Ticket ID: Info-only
  * Original item: Out of scope: “Remote MCP transport…”

    * Assigned Ticket ID: Info-only
  * Original item: Repro steps: LM Studio Windows misconfig (env array, Unix paths, WSL-only exe) → spawn failure

    * Assigned Ticket ID: T3
  * Original item: Environment section bullets

    * Assigned Ticket ID: Info-only
  * Original item: Evidence section bullets

    * Assigned Ticket ID: Info-only
  * Original item: Decisions: “User selected… pipx + uvx docs… PyPI project exists… assistant: don’t store artifacts in install dir”

    * Assigned Ticket ID: Info-only
  * Original item: Open item: “Canonical executable name… `lmstxt-mcp` vs `llmstxt-mcp`”

    * Assigned Ticket ID: T1
  * Original item: Open item: “Whether to implement MCP Roots support and/or OS user-data fallback…”

    * Assigned Ticket ID: T5
  * Original item: Open item: “First release version/tag name… not provided”

    * Assigned Ticket ID: T6
  * Original item: Open item: “Exact LM Studio error message(s)… not transcribed”

    * Assigned Ticket ID: T3
  * Original item: Risks bullets (Windows requires Windows-runnable install; `pipx run`/`uvx` latency; `~`/`$VARS` expansion unreliable; artifacts-root changes risk breakage)

    * Assigned Ticket ID: T3 (Windows + config expansion) / T2 (`pipx run`/`uvx` latency guidance) / T4 (artifacts-root change risk)
  * Original item: Acceptance Criteria checklist (README recommended + try; naming matches scripts; configs exist; artifacts docs; release checklist + smoke test)

    * Assigned Ticket ID: T1 / T2 / T3 / T4 / T6 (per item)

* Dependencies:

  * T2 depends on T1 because README install/run instructions must reference the finalized canonical executable name and base dependencies.
  * T3 depends on T1 because client configs must reference the finalized canonical executable name.
  * T6 depends on T1 because release packaging validation requires the finalized scripts/dependencies configuration.
  * T4 depends on T2 because artifacts-root UX documentation should align with documented `cwd`/default-path guidance (if used).

* Split Tickets:

```ticket T1
T# Title:
- Standardize canonical executable name + packaging scripts/dependencies
Type:
- chore
Target Area:
- Packaging (`pyproject.toml`), entrypoints (`[project.scripts]`), install-time dependencies
Summary:
- Align the MCP executable naming across docs/configs by selecting one canonical command (`lmstxt-mcp` vs `llmstxt-mcp`) and ensuring `pyproject.toml` scripts match. Ensure runtime dependencies required for the MCP server are included in the base install so `pipx`/`uv` execution works without dev extras.
In Scope:
- Choose one canonical MCP executable name and standardize it across:
  - `pyproject.toml` `[project.scripts]`
  - Documentation examples and client configs (referenced elsewhere; update references as needed)
- Ensure MCP server dependencies are available from the base install (not only dev extras)
- Ensure “package name differs from command name” is documented/handled consistently in launcher examples (`pipx run --spec ... <exe>`, `uvx --from ... <exe>`)
Out of Scope:
- Publishing an npm wrapper (`npx ...`) for the Python server
- Porting the server to TypeScript
Current Behavior (Actual):
- Inconsistent executable naming in examples (`lmstxt-mcp` vs `llmstxt-mcp`)
- Dependencies may be implied as dev-only, risking `pipx`/`uvx` runs from base install failing
Expected Behavior:
- One canonical executable name used everywhere and matches `pyproject.toml` scripts
- Base install contains all dependencies needed to run the stdio MCP server
Reproduction Steps:
- Not provided
Requirements / Constraints:
- “Ensure the canonical MCP executable name is consistent everywhere (docs + examples + `pyproject.toml` scripts).”
- “Ensure MCP server dependencies are not only available via dev extras…”
Evidence:
- Transcript reference: inconsistent naming (`lmstxt-mcp` vs `llmstxt-mcp`)
- Launch patterns referenced: `pipx run --spec ... <exe>` / `uvx --from ... <exe>`
Open Items / Unknowns:
- Canonical executable name to standardize: `lmstxt-mcp` vs `llmstxt-mcp` (must pick one and align)
Risks / Dependencies:
- Docs/config drift if executable name changes without synchronized updates (see dependencies on T2/T3/T6)
Acceptance Criteria:
- [ ] `pyproject.toml` defines the canonical executable under `[project.scripts]`
- [ ] All docs/examples/config snippets in-repo use that canonical executable name
- [ ] Base installation includes all dependencies needed to run the MCP stdio server (no dev-extras requirement)
Priority & Severity (if inferable from input text):
- Priority: Not provided
- Severity: Not provided
Source:
- “Ensure the canonical MCP executable name is consistent everywhere…”
- “Executable naming appears inconsistent… (`lmstxt-mcp` vs `llmstxt-mcp`).”
- “Ensure MCP server dependencies are not only available via dev extras…”
```

```ticket T2
T# Title:
- Update README install/run guidance (pipx/uv tool; optional pipx run/uvx; cwd)
Type:
- docs
Target Area:
- README / usage documentation (install/run story)
Summary:
- Document a single “install once, minimal friction” path using `pipx install <dist>` and/or `uv tool install <dist>` and running the installed executable. Add optional “try without install” examples (`pipx run --spec`, `uvx --from`) with version pinning, explicitly positioned as non-primary. Document `cwd` usage where supported to stabilize relative paths (especially artifacts defaults).
In Scope:
- Add README section: recommended install/run
  - `pipx install <dist>` and/or `uv tool install <dist>`
  - Run the installed canonical executable (from T1)
- Add README section: optional no-install/try-it commands (version pinned)
  - `pipx run --spec <dist>==X.Y.Z <exe>`
  - `uvx --from <dist>==X.Y.Z <exe>`
- Document when “no-install” launchers can be problematic (startup latency / implicit downloads) as a risk note
- Document `cwd` for clients that support it to stabilize relative paths
Out of Scope:
- Publishing npm wrapper / `npx` story as primary
Current Behavior (Actual):
- Docs create confusion about “no-install” vs “install once”
- Confusion around why `npx` is common but not applicable to a Python server without extra work
Expected Behavior:
- One recommended install/run path that “just works” via pipx/uv tool install
- Optional try-without-install path works but is clearly secondary
- Clear `cwd` guidance for clients that support it
Reproduction Steps:
- Not provided
Requirements / Constraints:
- “Add a ‘recommended’ install/run section using `pipx install <dist>` and/or `uv tool install <dist>`…”
- “Add optional ‘no-install / try it’ snippets… `pipx run --spec`… `uvx --from`…”
- “Document use of `cwd`… to stabilize relative paths…”
Evidence:
- “Docs/config guidance creates confusion about how to run… ‘no-install’ vs ‘install once’…”
Open Items / Unknowns:
- Not provided
Risks / Dependencies:
- Depends on T1 for finalized executable name used in docs
- `pipx run` / `uvx` may introduce startup latency when clients auto-start servers
Acceptance Criteria:
- [ ] README includes recommended install/run flow using pipx and/or `uv tool install`
- [ ] README includes optional no-install examples: `pipx run --spec <dist>==X.Y.Z <exe>` and `uvx --from <dist>==X.Y.Z <exe>`
- [ ] README documents `cwd` and how it affects relative paths
Priority & Severity (if inferable from input text):
- Priority: Not provided
- Severity: Not provided
Source:
- “Add a ‘recommended’ install/run section using `pipx install`…”
- “Add optional ‘no-install / try it’ snippets… `pipx run`… `uvx`…”
- “Document use of `cwd`… stabilize relative paths…”
```

```ticket T3
T# Title:
- Ship copy/paste MCP client configs (Claude Desktop, Cursor, Codex, LM Studio Windows) + Windows/WSL guidance
Type:
- docs
Target Area:
- Client configuration examples (JSON/TOML) + Windows/WSL compatibility guidance
Summary:
- Provide canonical, copy/pasteable MCP client configs for Claude Desktop, Cursor, Codex (`~/.codex/config.toml`), and LM Studio with a Windows-focused example. Ensure config examples use the correct `env` shape (object/map, not array), avoid assuming `~`/`$VARS` expansion, and clearly explain Windows vs WSL process spawning constraints.
In Scope:
- Create and publish canonical example configs for:
  - Claude Desktop (`claude_desktop_config.json`)
  - Cursor (`mcp.json`)
  - Codex (`~/.codex/config.toml`, including env / env_vars allowlist as referenced)
  - LM Studio (Windows-focused JSON example)
- Ensure examples:
  - Use the canonical executable name (from T1)
  - Use correct JSON shape for `env` (map/object, not array)
  - Use OS-appropriate paths (Windows paths in LM Studio example; avoid Unix `~`, `/home/...`)
  - Avoid shell-style env references (`$VAR`) in JSON/TOML examples
- Add explicit guidance:
  - Windows MCP clients spawning local processes require Windows-runnable commands
  - WSL-only installs will not be runnable by Windows-spawned LM Studio without remote transport
- Capture/record LM Studio error text if available in screenshots (if present in repo artifacts) as documentation evidence
Out of Scope:
- Implementing remote MCP transport (Streamable HTTP) as a solution (explicitly out of scope)
Current Behavior (Actual):
- LM Studio Windows config used malformed JSON (`env` as array) and Unix-style paths/expansions, causing spawn failures
- If server installed only in WSL, LM Studio on Windows cannot run it
- Clients may not expand `~` or `$VARS` reliably
Expected Behavior:
- Copy/paste configs exist for all listed clients and work with correct shapes/paths
- Docs explicitly prevent Windows/WSL mismatch confusion
Reproduction Steps:
1. In LM Studio on Windows, add an MCP server entry using Cursor-style format but:
   1) set `env` as an array instead of an object/map
   2) use Unix-style paths (`~`, `/home/...`) and shell-style env references (`$VAR`)
   3) point `command` to an executable installed only in WSL
2. Result: LM Studio fails to spawn/start the MCP server process (error text not provided; screenshots referenced)
Requirements / Constraints:
- “Provide canonical configs for… Claude Desktop… Cursor… Codex… LM Studio…”
- “LM Studio (Windows-focused example showing correct JSON shape and Windows paths)”
- “Cross-platform guidance is explicit… Windows… require Windows-runnable commands…”
Evidence:
- “In LM Studio… MCP JSON was malformed (env provided as an array)… Unix-style paths…”
- “Exact error text not provided; screenshots referenced.”
Open Items / Unknowns:
- Exact LM Studio error message(s) from screenshots: Not provided (not transcribed)
Risks / Dependencies:
- Depends on T1 for canonical executable name used in all configs
- Many clients do not reliably expand `~` or `$VARS`; examples must not assume expansion
Acceptance Criteria:
- [ ] Copy/paste configs exist for Claude Desktop, Cursor, Codex `config.toml`, and LM Studio (Windows)
- [ ] LM Studio example uses correct JSON `env` shape (object/map) and Windows-appropriate paths
- [ ] Docs explicitly state Windows clients require Windows-runnable installs; WSL-only installs will fail for Windows-spawned processes
- [ ] Examples avoid assuming `~` and `$VAR` expansion in JSON/TOML
Priority & Severity (if inferable from input text):
- Priority: Not provided
- Severity: Not provided
Source:
- “Provide canonical configs for… Claude Desktop… Cursor… Codex… LM Studio…”
- “In LM Studio… MCP JSON was malformed (env provided as an array)…”
- “Windows MCP clients… require the server… runnable on Windows (WSL-only installs will fail).”
```

```ticket T4
T# Title:
- Clarify artifacts-root UX + allowed-root safety model (env var + existing artifacts directory)
Type:
- docs
Target Area:
- Artifacts directory behavior, safety constraints, and user-facing documentation
Summary:
- Document the allowed-root boundary model (`LLMSTXT_MCP_ALLOWED_ROOT`) and make it easy to use an existing artifacts directory safely. Clarify default artifacts root behavior, how `output_dir` is validated within the allowed root (including the referenced `OutputDirNotAllowedError`), and expected directory structure for existing artifacts roots.
In Scope:
- Document allowed-root boundary concept:
  - `LLMSTXT_MCP_ALLOWED_ROOT`
  - `output_dir` must remain within the allowed root or error
- Document default artifacts root behavior (as currently implemented; do not invent behavior)
- Document “serve an existing artifacts directory”:
  - Set `LLMSTXT_MCP_ALLOWED_ROOT` to that directory
  - Expected structure: `<root>/<owner>/<repo>/...` (as referenced)
- Document why artifacts should not be stored in install directories (ephemeral/brittle)
- Include references to relevant tools/resources:
  - `lmstxt_list_all_artifacts`, `lmstxt_read_artifact`, `lmstxt://artifacts/...`
Out of Scope:
- Implementing MCP Roots support or OS user-data fallback (tracked separately in T5)
Current Behavior (Actual):
- Artifacts are guarded by allowed-root model; tool calls must keep `output_dir` within root or error (e.g., `OutputDirNotAllowedError`)
- UX for “use my existing artifacts dir” is not clear/easy
Expected Behavior:
- Users can understand default artifacts behavior and safely point to an existing artifacts directory via one setting
- Docs clearly state `output_dir` must be within allowed root
Reproduction Steps:
- Not provided
Requirements / Constraints:
- “Keep the allowed-root boundary concept and document it clearly…”
- “Document how to ‘serve an existing artifacts directory’ by setting `LLMSTXT_MCP_ALLOWED_ROOT`… expected structure…”
- “Do not store artifacts ‘wherever the package is installed’…”
Evidence:
- “Artifacts are guarded by an allowed-root model… `OutputDirNotAllowedError`…”
- “Resource URI pattern: `lmstxt://artifacts/...`”
Open Items / Unknowns:
- Default artifacts root behavior details beyond “default `./artifacts`” are not provided
Risks / Dependencies:
- Artifacts-root changes risk breaking existing users’ expectations if unspecified/ambiguous
Acceptance Criteria:
- [ ] Docs explain the allowed-root boundary (`LLMSTXT_MCP_ALLOWED_ROOT`) and that `output_dir` must be within it
- [ ] Docs explain default artifacts root behavior (only as implemented/documented; no invented semantics)
- [ ] Docs show how to use an existing artifacts directory by setting `LLMSTXT_MCP_ALLOWED_ROOT`, including expected `<root>/<owner>/<repo>/...` structure
- [ ] Docs explicitly warn against using install directories for artifacts storage
Priority & Severity (if inferable from input text):
- Priority: Not provided
- Severity: Not provided
Source:
- “Artifacts are guarded by an allowed-root model… (`LLMSTXT_MCP_ALLOWED_ROOT`, default `./artifacts`).”
- “Document how to ‘serve an existing artifacts directory’… expected structure…”
- “Do not store artifacts ‘wherever the package is installed’…”
```

```ticket T5
T# Title:
- Evaluate/implement artifacts-root enhancements (MCP Roots support, OS user-data fallback, resolved-path tool)
Type:
- enhancement
Target Area:
- Artifacts root resolution and client-integrated filesystem boundary controls
Summary:
- Implement the optional improvements discussed for artifacts-root handling: support MCP “Roots” (`roots/list`) when clients provide it to restrict IO to client-configured roots; otherwise fall back to a stable OS user-data directory. Add a tool that returns resolved paths (artifacts root and run output path) to reduce user guesswork.
In Scope:
- Add support for MCP Roots (`roots/list`) when the client provides it, using roots to restrict IO boundaries (as described)
- Add fallback behavior when Roots are unavailable:
  - Use a stable OS user-data directory (exact location not specified in the parent ticket)
- Add a tool that returns resolved paths:
  - Artifacts root
  - Run output path
Out of Scope:
- Remote MCP transport implementation
- Changing the allowed-root boundary concept (must be preserved)
Current Behavior (Actual):
- Artifacts access is controlled by `LLMSTXT_MCP_ALLOWED_ROOT` and `output_dir` validation within that root
- No MCP Roots integration or OS user-data fallback is described as implemented
Expected Behavior:
- When client provides Roots, server restricts IO to those roots
- When Roots are unavailable, server uses a stable user-data directory (instead of ephemeral install directories)
- Users can query resolved paths via a dedicated tool to remove guesswork
Reproduction Steps:
- Not provided
Requirements / Constraints:
- Must keep allowed-root boundary concept
- Do not store artifacts in install directories
- Improvements are explicitly framed as “Consider improvements discussed” (not yet committed)
Evidence:
- “Support MCP ‘Roots’ (`roots/list`) when the client provides it…”
- “Fallback to a stable OS user-data directory when Roots are unavailable.”
- “Add a tool that returns resolved paths…”
Open Items / Unknowns:
- Whether to implement MCP Roots support and/or OS user-data fallback vs env-var-only control: Not decided (per parent ticket)
- Exact OS user-data directory selection rules: Not provided
Risks / Dependencies:
- Artifacts-root changes may break expectations and/or security constraints if poorly specified
- May need alignment with T4 documentation once behavior changes
Acceptance Criteria:
- [ ] Server supports MCP Roots (`roots/list`) when provided and restricts IO to client-configured roots
- [ ] Server has a defined fallback to a stable OS user-data directory when Roots are unavailable (no install-dir storage)
- [ ] A tool exists to return resolved artifacts root and run output path
- [ ] Allowed-root boundary concept remains enforced
Priority & Severity (if inferable from input text):
- Priority: Not provided
- Severity: Not provided
Source:
- “Consider improvements… Support MCP ‘Roots’ (`roots/list`)…”
- “Fallback to a stable OS user-data directory when Roots are unavailable.”
- “Add a tool that returns resolved paths…”
```

```ticket T6
T# Title:
- Release readiness: build validation, smoke tests, and first tag/versioning checklist
Type:
- chore
Target Area:
- Release process (PyPI publish), validation checklist, tag/version handling
Summary:
- Create a pre-tag release checklist that validates build and a clean install smoke test of the MCP executable from a fresh environment. Ensure guidance accounts for tag-derived versioning (e.g., `setuptools_scm` mentioned in discussion) where pushing the first tag is required to produce a clean release version.
In Scope:
- Add “pre-tag validation” checklist steps:
  - Build
  - Smoke test: installed command execution from a fresh environment
- Document tag/versioning considerations as applicable:
  - If versioning is tag-derived, first tag is required for clean release version
- Capture the known project readiness state in release notes/checklist:
  - Project renamed in `pyproject.toml` and remote main branch
  - PyPI project exists and is ready for pushing tags (release)
Out of Scope:
- Changing packaging strategy beyond what’s required for release readiness (handled in T1)
Current Behavior (Actual):
- Release is pending; first tag/version selection not provided
- Packaged distribution/run story still being standardized; smoke-test flow not formalized
Expected Behavior:
- A repeatable release checklist exists and a clean build + install smoke test runs successfully
- First tag can be pushed to publish the PyPI release with a clean version
Reproduction Steps:
- Not provided
Requirements / Constraints:
- “Pre-tag validation: build + smoke test installed command execution…”
- “If versioning is tag-derived… pushing the first tag is required…”
Evidence:
- “PyPI project exists and is ready for tagging/publishing.”
- “First release version/tag name… not provided.”
Open Items / Unknowns:
- First release version/tag name to publish: Unknown (examples given were illustrative only)
Risks / Dependencies:
- Depends on T1 for correct scripts/dependencies prior to smoke testing
Acceptance Criteria:
- [ ] Release checklist exists (build + fresh-environment install + run smoke test)
- [ ] Checklist documents tag/versioning requirement if tag-derived (first tag required for clean version)
- [ ] Checklist is sufficient to proceed with pushing the first tag and publishing to PyPI (given dependencies satisfied)
Priority & Severity (if inferable from input text):
- Priority: Not provided
- Severity: Not provided
Source:
- “Pre-tag validation: build + smoke test installed command execution…”
- “pushing the first tag is required for a clean release version.”
- “PyPI project exists and is ready for pushing tags (release).”
```
