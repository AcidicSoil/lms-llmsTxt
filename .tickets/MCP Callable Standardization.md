Parent Ticket:

* Title: Standardize `lms-llmsTxt` MCP callable story (pipx/uvx vs npx), client configs, Windows/WSL behavior, and artifacts-root handling
* Summary:

  * The project is a Python FastMCP stdio server with confusion/friction around: how users run/install it (pipx/uvx vs npx), inconsistent executable naming in docs/configs, Windows vs WSL process spawning for LM Studio, and how to safely point the server at an existing `artifacts/` directory.
* Source:

  * Link/ID (if present) or “Not provided”: /mnt/data/Branch · MCP callable options via npx.md
  * Original ticket excerpt (≤25 words) capturing the overall theme: “Standardize … distribution/run story … client configs … Windows vs WSL … artifacts-root strategy.”
* Global Constraints:

  * “One command, minimal friction”
  * “We just want it to work”
  * Do not rely on `npx` unless explicitly chosen as a supported distribution path
* Global Environment:

  * Python FastMCP stdio server
  * MCP clients discussed: Claude Desktop, Cursor, Codex, LM Studio
  * OS contexts discussed: Windows + WSL/Linux
  * Env vars discussed: `GITHUB_ACCESS_TOKEN`, `LMSTUDIO_BASE_URL`, `LLMSTXT_MCP_ALLOWED_ROOT` (plus optional `LMSTUDIO_API_KEY`, `LMSTUDIO_MODEL`, `OUTPUT_DIR`, `ENABLE_CTX=1`)
* Global Evidence:

  * `https://modelcontextprotocol.io/docs/develop/connect-local-servers`
  * `https://modelcontextprotocol.io/examples`
  * `https://lmstudio.ai/docs/app/mcp`
  * `https://developers.openai.com/codex/mcp/`
  * `https://pipx.pypa.io/`
  * `https://docs.astral.sh/uv/`
  * `https://learn.microsoft.com/en-us/windows/wsl/networking`

Split Plan:

* Coverage Map:

  * Original item: “What’s the next step for making the mcp callable via npx or what are my options…?”

    * Assigned Ticket ID: T7
  * Original item: “Option 1 (recommended): ship ‘one-command run’ for Python users (pipx / uvx)… update README…”

    * Assigned Ticket ID: T2
  * Original item: “Ensure the MCP server isn’t hidden behind `[dev]`… ensure entry points in `pyproject.toml`…”

    * Assigned Ticket ID: T2
  * Original item: “Lock the public ‘server command’ name… `lmstxt-mcp` vs `llmstxt-mcp`… update README/examples…”

    * Assigned Ticket ID: T1
  * Original item: “MCP configs: clients run the executable you publish… pick one name and make consistent…”

    * Assigned Ticket ID: T3
  * Original item: “Copy/paste configs for Claude Desktop / Cursor… installed and no-install (uvx/pipx run) variants…”

    * Assigned Ticket ID: T3
  * Original item: “Codex config.toml examples (`command`, optional `args`, `env`, `env_vars`)…”

    * Assigned Ticket ID: T3
  * Original item: “LM Studio error: `env` malformed JSON (array vs map), Unix-style paths, `$VAR`/`~` not expanded…”

    * Assigned Ticket ID: T4
  * Original item: “LM Studio spawns local process on Windows; server must be runnable on Windows (PATH)…”

    * Assigned Ticket ID: T4
  * Original item: “How do users install for both sides? … install in same OS environment where client runs…”

    * Assigned Ticket ID: T4
  * Original item: “WSL networking for `LMSTUDIO_BASE_URL` (localhost vs Windows host IP)…”

    * Assigned Ticket ID: T4
  * Original item: “What does `cwd` do? … affects relative paths like `./artifacts`…”

    * Assigned Ticket ID: Info-only
  * Original item: “How does a user add an artifact directory / provide an existing artifacts dir? … `LLMSTXT_MCP_ALLOWED_ROOT` and `output_dir` must be inside…”

    * Assigned Ticket ID: T5
  * Original item: “Artifacts layout expectations (`<root>/<owner>/<repo>/...`) and listing/reading artifacts…”

    * Assigned Ticket ID: T5
  * Original item: “Do I need to test and push first tag now? … pre-tag validation, tag+publish, post-publish checks…”

    * Assigned Ticket ID: T6
  * Original item: “Why do most MCP servers use npx over uvx?”

    * Assigned Ticket ID: Info-only
  * Original item: “Option 2A thin wrapper vs 2B binaries; Option 3 TS port; Option 4 remote HTTP…”

    * Assigned Ticket ID: T7
  * Original item: “If LM Studio can’t find `llmstxt-mcp` in PowerShell, `cwd` won’t help…”

    * Assigned Ticket ID: T4
* Dependencies:

  * T2 depends on T1 because install/run docs must reference the final canonical executable name.
  * T3 depends on T1 because client configs must reference the final canonical executable name.
  * T4 depends on T1 because Windows/LM Studio guidance must reference the final canonical executable name.
  * T5 depends on T1 because artifact-root docs and examples must reference the final canonical executable name.
  * T6 depends on T1 because release artifacts must contain the correct scripts and documentation references.
* Split Tickets:

```ticket T1
T# Title:
- Standardize the canonical MCP executable name and align all references

Type:
- chore

Target Area:
- Packaging metadata (`pyproject.toml` scripts) + docs/examples referencing the MCP command

Summary:
- There is an inconsistency between the executable name referenced in examples and the executable name defined/shipped. Pick a single canonical MCP server command and make all docs and client config examples match it. This prevents “command not found” and cross-client startup failures.

In Scope:
- Choose canonical MCP executable name (`lmstxt-mcp` vs `llmstxt-mcp`) and apply consistently.
- Ensure `[project.scripts]` exports the canonical executable and points to the correct module path after the rename/restructure.
- Update README/config examples that reference the non-canonical name to the canonical one.
- Ensure any “verify command exists” instructions reference the canonical command.

Out of Scope:
- Not provided

Current Behavior (Actual):
- Examples reference one command name while packaging metadata references another, causing user confusion and startup errors in clients.

Expected Behavior:
- One canonical MCP executable name exists.
- All docs and client configs reference the same canonical command.
- The published package installs that canonical command successfully.

Reproduction Steps:
1. Follow a README/client example that references the non-installed command name.
2. Observe the client fails to spawn the MCP server / OS cannot find the command.

Requirements / Constraints:
- Canonical name decision must be reflected in both packaging metadata and documentation.

Evidence:
- Mentioned mismatch between `pyproject.toml` scripts and README examples.
- Mentioned “entrypoint is `llmstxt-mcp` … not `lmstxt-mcp`”.

Open Items / Unknowns:
- Which canonical command name is desired (`lmstxt-mcp` or `llmstxt-mcp`) is not provided.

Risks / Dependencies:
- Depends on: None (but unblocks T2–T6).

Acceptance Criteria:
- [ ] `pyproject.toml` exposes exactly one canonical MCP server command in `[project.scripts]`.
- [ ] All README/client examples use the canonical command name.
- [ ] A “verify install” step references the canonical command (e.g., `where ...` / `which ...`) and matches actual behavior.

Priority & Severity (if inferable from input text):
- Priority: Not provided
- Severity: Not provided

Source:
- “Decide the canonical MCP executable name: `lmstxt-mcp` **or** `llmstxt-mcp`.”
- “Your `pyproject.toml` shows `llmstxt-mcp = ...` … README examples use `lmstxt-mcp`…”
```

```ticket T2
T# Title:
- Make pipx/uvx the primary “one-command” install/run path and ensure it works without dev extras

Type:
- chore

Target Area:
- README install/run documentation + dependency/extras layout for MCP command

Summary:
- The intended “minimal friction” path is pipx/uvx (Python’s closest analogue to `npx`). Document these commands as the primary path and ensure the MCP server command is available from the base install (or a dedicated non-dev extra), not hidden behind `[dev]`.

In Scope:
- Add/refresh README section: “One-command install/run (recommended)” using pipx + uvx.
- Include both persistent install (`pipx install ...`) and ephemeral run (`pipx run --spec ... <exe>` / `uvx --from ... <exe>`).
- Ensure the MCP server command is available without requiring `[dev]` (or document a dedicated extra like `[mcp]` if that is the chosen contract).

Out of Scope:
- Full `npx` distribution (handled in T7).

Current Behavior (Actual):
- The doc path relies on editable installs and/or dev extras in examples, which is not aligned with pipx/uvx expectations.

Expected Behavior:
- Users can run the MCP server via:
  - install-once: pipx tool install then run canonical command
  - one-off: uvx/pipx run invocation
- This works without installing dev-only extras.

Reproduction Steps:
1. Follow current docs requiring `pip install -e .[dev]`.
2. Attempt to translate that to pipx/uvx usage.
3. Observe friction/confusion if MCP command isn’t available from base install.

Requirements / Constraints:
- Must keep “package name vs command name” mismatch explicit where it exists (pipx `--spec`, uvx `--from` usage).
- Avoid requiring `[dev]` for runtime usage.

Evidence:
- Explicit recommendation to “update your README with … pipx/uvx”.
- Explicit note: “Ensure the MCP server isn’t hidden behind `[dev]`”.

Open Items / Unknowns:
- Whether to expose MCP deps in base install vs a dedicated extra is not provided.
- The release version to pin in docs is not provided.

Risks / Dependencies:
- Depends on: T1 (docs must use the canonical command name).

Acceptance Criteria:
- [ ] README contains pipx install + pipx run examples for the canonical executable.
- [ ] README contains uvx run example for the canonical executable.
- [ ] MCP server command runs when installed via pipx without requiring dev extras.
- [ ] If an extra is required, it is documented explicitly and is not named `[dev]`.

Priority & Severity (if inferable from input text):
- Priority: Not provided
- Severity: Not provided

Source:
- “Option 1 (recommended): ship ‘one-command run’ … (pipx / uvx)… update your README…”
- “Ensure the MCP server isn’t hidden behind `[dev]`.”
- “pipx run --spec … / uvx --from …”
```

```ticket T3
T# Title:
- Publish canonical copy/paste MCP client configs (Claude Desktop, Cursor, Codex) aligned to shipped command

Type:
- docs

Target Area:
- Documentation: client configuration examples and security notes

Summary:
- Users need consistent, copy/pasteable MCP configuration blocks across popular clients. Provide canonical examples that run the shipped executable directly, plus optional “no-install” runner variants (pipx/uvx) where applicable. Include both “static env in config” and “forward env vars” variants where discussed.

In Scope:
- Claude Desktop config example(s) referencing canonical MCP command.
- Cursor config example(s) referencing canonical MCP command.
- Codex `~/.codex/config.toml` example(s) including:
  - `command`, optional `args`
  - `[mcp_servers.<name>.env]` usage
  - `env_vars = [...]` allowlist variant (to avoid storing secrets)
- Optional “no-install” variants using `uvx --from ...` and `pipx run --spec ...` (version pinned where applicable).

Out of Scope:
- LM Studio-specific troubleshooting and Windows spawning behavior (handled in T4).

Current Behavior (Actual):
- Examples exist but are inconsistent with the actual shipped executable name and mixed patterns cause user errors.

Expected Behavior:
- A single canonical set of config examples exists and matches the shipped command name.
- Examples clearly show correct JSON/TOML shapes and where env belongs.

Reproduction Steps:
1. Copy a config example into a client config.
2. Start client; server fails to spawn if command name is inconsistent or env shape is incorrect.

Requirements / Constraints:
- Keep secrets redacted/placeholders (no real tokens in docs).
- Config examples must match each client’s expected schema (JSON for Claude/Cursor; TOML for Codex).

Evidence:
- Multiple provided example blocks for Claude/Cursor and Codex.
- Mentioned Codex supports `env_vars` allowlist.

Open Items / Unknowns:
- Final version number to pin in examples is not provided.

Risks / Dependencies:
- Depends on: T1 (canonical command naming).

Acceptance Criteria:
- [ ] Docs contain Claude Desktop JSON example using canonical command.
- [ ] Docs contain Cursor JSON example using canonical command.
- [ ] Docs contain Codex TOML example using canonical command and optional `args = []`.
- [ ] Docs contain Codex `env_vars = [...]` variant.
- [ ] Optional: docs include uvx/pipx runner variants and clearly label them as optional.

Priority & Severity (if inferable from input text):
- Priority: Not provided
- Severity: Not provided

Source:
- “Clients don’t ‘call the PyPI project name’; they run the executable you publish…”
- “Codex supports `env_vars` as ‘allow and forward’ environment variables.”
- “Below are the exact configs… Claude Desktop … Cursor …”
```

```ticket T4
T# Title:
- Document and fix Windows + LM Studio MCP spawning pitfalls (env shape, paths, PATH installation, WSL considerations)

Type:
- docs

Target Area:
- Documentation: LM Studio + Windows/WSL setup and troubleshooting guidance

Summary:
- LM Studio spawns stdio MCP servers as local Windows processes, so the server must be installed/runnable on Windows if LM Studio runs on Windows. Document the common failure modes (bad `mcp.json` env shape, Unix paths, non-expanded env references, missing executable on PATH) and provide a known-good Windows configuration pattern including optional `cwd`.

In Scope:
- Clarify that MCP stdio servers must be installed in the same OS environment as the client that spawns them.
- LM Studio `mcp.json` correctness notes:
  - `env` must be an object/map (not an array)
  - avoid `~` and shell-style `$VARS` expecting expansion
  - use absolute Windows paths where needed
- Troubleshooting checklist for Windows:
  - `where <canonical-command>`
  - `<canonical-command> --help`
- Explain WSL split-install scenario (Codex in WSL vs LM Studio on Windows).
- Note WSL networking caveat for `LMSTUDIO_BASE_URL` when server runs in WSL but LM Studio runs on Windows (localhost vs host IP).

Out of Scope:
- Changing transport from stdio to remote HTTP (only discussed as an option; implementation belongs in T7 if chosen).

Current Behavior (Actual):
- Users encounter LM Studio startup errors due to invalid JSON shape, wrong command name, missing Windows install, and path/env expansion assumptions.

Expected Behavior:
- Users can follow a single Windows-specific doc section to configure LM Studio successfully.
- Users understand when they must install twice (Windows + WSL) based on where clients run.

Reproduction Steps:
1. Configure LM Studio with `env` as an array or with Unix paths / `$VARS`.
2. Start LM Studio MCP; observe spawn error / command not found.

Requirements / Constraints:
- Keep credentials redacted/placeholders.

Evidence:
- “Your `env` is malformed JSON … must be a map/object”
- “LM Studio … spawns … on Windows … must be runnable from Windows (PATH)”
- “install … in the same OS environment where the client is running”
- WSL networking note using `/etc/resolv.conf` nameserver.

Open Items / Unknowns:
- Whether LM Studio users are expected to run the server in WSL vs Windows is not provided.

Risks / Dependencies:
- Depends on: T1 (canonical command name).

Acceptance Criteria:
- [ ] Docs include an LM Studio Windows example with correct `env` object shape.
- [ ] Docs explicitly state server must be installed on Windows when LM Studio runs on Windows.
- [ ] Docs include a minimal verification checklist (`where` + `--help`).
- [ ] Docs mention WSL networking caveat for `LMSTUDIO_BASE_URL` when crossing Windows/WSL.

Priority & Severity (if inferable from input text):
- Priority: Not provided
- Severity: Not provided

Source:
- “LM Studio is trying to spawn your MCP server as a local process on Windows…”
- “Your `env` is malformed JSON… `env` must be a map/object…”
- “LM Studio Desktop on Windows ⇒ install … on Windows … Codex CLI inside WSL ⇒ install … inside WSL”
```

```ticket T5
T# Title:
- Standardize and document artifacts directory configuration (allowed root, existing artifacts, path/cwd interactions)

Type:
- docs

Target Area:
- Documentation: artifact root strategy and user guidance across clients/OSes

Summary:
- Users need a clear, safe way to point the MCP server at an existing artifacts directory and understand how `LLMSTXT_MCP_ALLOWED_ROOT`, tool `output_dir`, and process `cwd` interact. Document the contract: `output_dir` must be inside the allowed root, default behavior for `./artifacts`, and what directory layout is expected for existing artifacts.

In Scope:
- Document how to set `LLMSTXT_MCP_ALLOWED_ROOT` via MCP client `env`.
- Document/clarify that any `output_dir` passed to tools must be inside the allowed root.
- Document recommended layout expectations (root / owner / repo / files) as described.
- Document “avoid accidental `.../artifacts/artifacts`” pitfall when combining allowed-root + `cwd` + default `./artifacts`.
- Document how users list/read existing artifacts via the described tool/resource patterns.

Out of Scope:
- Changing server behavior to a different artifacts-root strategy (only discussed as a question; not specified as a requirement here).

Current Behavior (Actual):
- Users are unsure how to “add” or reuse an artifacts directory safely; path/cwd interactions can cause confusing nested output locations.

Expected Behavior:
- Users can:
  - set an allowed artifacts root,
  - generate into a directory inside it,
  - and/or serve/read pre-existing artifacts in that root,
  without unexpected path nesting.

Reproduction Steps:
1. Set `LLMSTXT_MCP_ALLOWED_ROOT` to a subdirectory like `.../artifacts`.
2. Run a tool that defaults to `./artifacts` with an unexpected `cwd`.
3. Observe outputs landing in `.../artifacts/artifacts` (pitfall described).

Requirements / Constraints:
- Cross-OS examples must use correct path styles (Windows vs Linux).

Evidence:
- Mentioned enforcement: `output_dir` must be inside `LLMSTXT_MCP_ALLOWED_ROOT`.
- Mentioned pitfall and recommendation: set allowed root to project root to make `./artifacts` predictable.

Open Items / Unknowns:
- Whether the default allowed root should be changed is not provided.

Risks / Dependencies:
- Depends on: T1 (canonical command name) and aligns with T4 (Windows path guidance).

Acceptance Criteria:
- [ ] Docs explain `LLMSTXT_MCP_ALLOWED_ROOT` purpose and how to set it in clients.
- [ ] Docs explicitly state the `output_dir` containment requirement.
- [ ] Docs include an example for reusing an existing artifacts directory.
- [ ] Docs call out the `cwd`/default `./artifacts` nesting pitfall and how to avoid it.

Priority & Severity (if inferable from input text):
- Priority: Not provided
- Severity: Not provided

Source:
- “Any `output_dir` passed to tools must be inside that allowed root…”
- “If you set the allowed root to `.../artifacts`, you can accidentally end up with `.../artifacts/artifacts`…”
- “How does a user add an artifact directory ? or provide an already existing artifact/ dir?”
```

```ticket T6
T# Title:
- Define and execute the release checklist for the renamed PyPI project (pre-tag validation, tag+publish, smoke tests)

Type:
- chore

Target Area:
- Release process + CI/release automation references

Summary:
- The project has been renamed and a PyPI project is ready; release should follow a documented checklist: validate locally, tag, publish, then verify installation and MCP server startup in clean environments. Ensure release automation references the renamed project correctly.

In Scope:
- Pre-tag validation steps:
  - run tests (e.g., `pytest` if used)
  - build distributions
  - verify distribution metadata
  - smoke-test install and run the MCP command from built artifacts
- Tag + publish steps:
  - create version tag (e.g., `v0.1.0` as referenced)
  - push tag to trigger publishing workflow (if used)
- Post-publish verification:
  - install via pipx/uv tool install in a clean environment
  - run canonical MCP server command
- Update any CI/CD publish workflows that reference the old project name (as noted).

Out of Scope:
- Implementing new distribution methods (e.g., npx wrapper/binaries) beyond what’s already planned (handled in T7 if chosen).

Current Behavior (Actual):
- Release is “ready to push tags,” but an explicit runbook/checklist is needed to ensure callability and consistency across clients.

Expected Behavior:
- A repeatable release process exists and is executed successfully for the first tag.
- Published package installs cleanly and exposes the canonical MCP command.

Reproduction Steps:
1. Publish without running pre-tag checks or without aligning scripts/docs.
2. Users attempt to install/run via pipx/clients and encounter missing command or mismatch.

Requirements / Constraints:
- Versioning/tagging approach may be driven by SCM tags (setuptools_scm was referenced).

Evidence:
- Included “Checklist (release + client-callability)” with pre-tag, tag+publish, post-publish verification.
- Mentioned “ready to push tags.”

Open Items / Unknowns:
- Exact first release version/tag is not provided.
- Exact CI trigger mechanism is not provided.

Risks / Dependencies:
- Depends on: T1 (canonical scripts/docs alignment), supports T2/T3/T4/T5 accuracy.

Acceptance Criteria:
- [ ] Pre-tag build + smoke-test passes for canonical MCP command.
- [ ] First tag is created and pushed and publishing completes (per project workflow).
- [ ] Post-publish: `pipx install <pypi-name>` exposes the canonical MCP command and it runs.
- [ ] Release automation references the renamed project name consistently.

Priority & Severity (if inferable from input text):
- Priority: Not provided
- Severity: Not provided

Source:
- “renaming is done … pypi project created and ready to push tags…”
- “Checklist (release + client-callability) … Pre-tag … Tag + publish … validate in a totally clean environment…”
```

```ticket T7
T# Title:
- Decide and (if required) implement an `npx`-callable distribution path for the Python MCP server

Type:
- enhancement

Target Area:
- Distribution strategy + optional Node wrapper package for `npx`

Summary:
- Users asked for making the MCP “callable via `npx`”. For a Python MCP server, `npx` requires an npm package that provides a `bin` entry. The ticket includes multiple options: a thin wrapper that requires Python already installed (2A), shipping binaries (2B), porting to TypeScript (3), or hosting remotely over HTTP (4). Decide which option is supported and implement/document accordingly.

In Scope:
- Record the supported `npx` approach selection from the listed options (2A/2B/3/4).
- If selecting 2A (thin wrapper):
  - Create/publish an npm wrapper package whose `bin` launches the Python MCP server (shelling out to `python -m ...` or the installed console script, as described).
  - Document prerequisites and usage (`npx <pkg>` expectation).
- If selecting 2B/3/4:
  - Document the selected approach and its operational requirements (as described in the source text).

Out of Scope:
- Unrelated feature development in the MCP server itself.

Current Behavior (Actual):
- `npx` is not inherently supported for a Python-distributed MCP server without an npm wrapper/binary distribution.

Expected Behavior:
- The project has a clear, documented stance on `npx` support.
- If implemented, `npx` invocation can start the MCP server under the documented prerequisites.

Reproduction Steps:
1. Attempt to run the Python MCP via `npx` without an npm package wrapper.
2. Observe that `npx` cannot run non-npm distributions directly.

Requirements / Constraints:
- If using 2A, Python is still required on the target machine.
- If using 2B, multi-OS binary build/release complexity applies.

Evidence:
- Explicit “Option 2: make it runnable via npx (Node wrapper package)” with 2A/2B details.
- Additional options: TS port (3) and remote HTTP (4).

Open Items / Unknowns:
- Whether `npx` is a hard requirement vs an optional path is not provided.
- Which of 2A/2B/3/4 is desired is not provided.

Risks / Dependencies:
- Depends on: T1 (canonical command naming) and T6 (release/publish process) if an npm package is added.

Acceptance Criteria:
- [ ] Docs list supported distribution/run methods and explicitly address `npx`.
- [ ] If 2A selected: an npm package exists with a `bin` that launches the MCP server as described.
- [ ] If 2A selected: running `npx <wrapper>` starts the MCP server under documented prerequisites.

Priority & Severity (if inferable from input text):
- Priority: Not provided
- Severity: Not provided

Source:
- “Option 2: make it runnable via `npx` (Node wrapper package)”
- “2A) Thin wrapper that requires Python already installed”
- “2B) ‘Real’ npx experience: ship platform binaries via npm”
```

Non-actionable / Info-only (preserved):

* “`cwd` means current working directory … relative paths are resolved against it … `./artifacts` resolves under `cwd`.”
* “Most MCP servers use `npx` because many are Node/TypeScript packages; `uvx` is Python-specific and less universally installed.”
