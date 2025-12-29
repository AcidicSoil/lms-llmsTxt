## 1) Overview

### Problem

Publishing `lmstudio-llmstxt-generator` to PyPI should be repeatable, secure, and verifiable, but the current state has multiple likely failure points:

* The package declares a direct VCS URL dependency (`llm-ctx @ git+...`), which PyPI rejects as an invalid `Requires-Dist` in common cases.  ([GitHub][1])
* The repository uses a `src/` layout (package code under `src/lmstudiotxt_generator`), but `pyproject.toml` currently lacks explicit setuptools package discovery configuration, risking “empty” wheels (install succeeds but imports fail).
* CI publishing workflows exist (PyPI on tag, TestPyPI on manual dispatch), but need alignment with packaging constraints, dependency correctness, and end-to-end verification.

### Target users

* **Maintainers / releasers**: want a single, low-friction release process (tag → publish), with confidence via checks and smoke tests.
* **Contributors**: want changes to packaging/release to be safe and testable in PRs.
* **Downstream users**: want `pip install lmstudio-llmstxt-generator` and `lmstxt --help` to work reliably.

### Why current solutions fail

* Packaging metadata can be rejected by PyPI due to direct URL dependencies.  ([GitHub][1])
* `src/` layout without explicit discovery config is a common source of missing-package artifacts.
* Publishing without deterministic verification allows broken installs to ship.

### Success metrics

* **Release reliability**: Tag-triggered publish completes with no manual steps beyond tagging; smoke tests pass for both wheel and sdist.
* **Acceptance**: PyPI upload succeeds (no metadata rejection).
* **Install verification**: Fresh install from PyPI runs `lmstxt --help` successfully.
* **Reproducibility**: TestPyPI publish path available for preflight testing.

Assumptions (explicit):

* GitHub Actions is the canonical CI environment.
* Publishing uses `uv build` / `uv publish` as in existing workflows.
* Trusted publishing (OIDC) is preferred for PyPI releases. ([PyPI Docs][2])

---

## 2) Capability Tree (Functional Decomposition)

### Capability: Packaging Configuration & Compliance

Ensures metadata/build configuration is PyPI-acceptable and produces correct artifacts.

#### Feature: Dependency compliance (no direct URL deps) **[MVP]**

* **Description**: Replace disallowed VCS/direct-URL dependencies with PyPI-resolvable requirements.
* **Inputs**: `pyproject.toml` dependency list.
* **Outputs**: Updated dependency declarations accepted by PyPI.
* **Behavior**: Detect `@ git+...` style requirements and replace with normalized package requirement specifiers; block release if any remain. ([GitHub][1])

#### Feature: `src/` layout package discovery **[MVP]**

* **Description**: Configure setuptools to discover packages under `src/`.
* **Inputs**: Repository layout; `pyproject.toml`.
* **Outputs**: Wheel/sdist containing `lmstudiotxt_generator` package.
* **Behavior**: Declare `package-dir` and `packages.find` (or equivalent) so builds include the package code under `src/`.

#### Feature: Dependency name correctness (distribution vs import) **[MVP]**

* **Description**: Ensure declared dependencies match their actual PyPI distribution names.
* **Inputs**: Declared deps (e.g., `llms_txt`); PyPI canonical names.
* **Outputs**: Dependencies that resolve via `pip` from PyPI.
* **Behavior**: Normalize underscores/hyphens to canonical distribution names (e.g., `llms-txt` on PyPI). ([PyPI][3])

---

### Capability: Local Build & Preflight Validation

Enables maintainers to validate artifacts before publishing.

#### Feature: Local build (sdist + wheel) **[MVP]**

* **Description**: Build distributable artifacts locally in a clean state.
* **Inputs**: Repo source tree, `pyproject.toml`.
* **Outputs**: `dist/*.whl`, `dist/*.tar.gz`.
* **Behavior**: Clean previous artifacts, run standard build, ensure both artifact types exist.

#### Feature: Artifact metadata validation **[MVP]**

* **Description**: Validate built artifacts are well-formed for upload.
* **Inputs**: Built `dist/*` artifacts.
* **Outputs**: Pass/fail with actionable error output.
* **Behavior**: Run an artifact check step (e.g., `twine check` or equivalent) and fail fast on metadata errors.

#### Feature: Local install + CLI smoke check **[MVP]**

* **Description**: Ensure the built artifacts install and expose the CLI.
* **Inputs**: Built artifacts; declared console script `lmstxt`.
* **Outputs**: Pass/fail; CLI help output reachable.
* **Behavior**: Install from wheel/sdist into an isolated env and run `lmstxt --help`.

---

### Capability: CI Publishing (TestPyPI + PyPI)

Automates publishing with appropriate authentication and gating checks.

#### Feature: TestPyPI manual publish workflow **[MVP]**

* **Description**: Publish a chosen ref/tag to TestPyPI for preflight.
* **Inputs**: Git ref/tag (workflow_dispatch input); TestPyPI credentials.
* **Outputs**: Uploaded artifacts on TestPyPI index.
* **Behavior**: Checkout ref, build distributions, publish to TestPyPI index.

#### Feature: PyPI tag-based release workflow with trusted publishing **[MVP]**

* **Description**: Publish to PyPI automatically when a `v*` tag is pushed, using OIDC.
* **Inputs**: Git tag `vX.Y.Z`; GitHub Actions OIDC token; PyPI Trusted Publisher configuration.
* **Outputs**: Release artifacts available on PyPI.
* **Behavior**: Build, run smoke tests on wheel & sdist, publish using OIDC-based trusted publishing (no long-lived token).  ([PyPI Docs][2])

#### Feature: CI smoke testing of built artifacts **[MVP]**

* **Description**: Validate wheel and sdist in CI prior to publish.
* **Inputs**: Built artifacts; smoke test script(s).
* **Outputs**: Pass/fail gating for publishing.
* **Behavior**: Run an isolated smoke test against both artifact types (wheel + sdist) as done in the existing workflow.

---

### Capability: Documentation & Operator Guidance

Makes the release process discoverable and repeatable.

#### Feature: Publish runbook (local + CI) **[MVP]**

* **Description**: Single document describing how to release, verify, and troubleshoot.
* **Inputs**: Existing steps; workflow definitions.
* **Outputs**: Maintainer-facing doc checked into repo.
* **Behavior**: Document prerequisites (accounts/tokens/trusted publisher), local checks, TestPyPI preflight, tag release, verification steps.

---

## 3) Repository Structure + Module Definitions (Structural Decomposition)

### Proposed repository structure (release-related)

```
pyproject.toml
.github/
  workflows/
    release.yml
    publish-testpypi.yml
docs/
  publishing.md
tests/
  smoke_test.py
scripts/
  release/
    validate_metadata.py
    verify_install.sh
```

### Module: Packaging manifest

* **Maps to capability**: Packaging Configuration & Compliance
* **Responsibility**: Declare build system, metadata, dependencies, package discovery.
* **File**: `pyproject.toml`
* **Exports (conceptual)**:

  * Project metadata (`[project]`)
  * Dependency set (`[project].dependencies`)
  * Console scripts (`[project.scripts]` → `lmstxt`)
  * Build backend (`[build-system]`)
  * Setuptools discovery config (to be added)

### Module: PyPI release workflow

* **Maps to capability**: CI Publishing (PyPI)
* **Responsibility**: Build, smoke-test, publish on `v*` tag.
* **File**: `.github/workflows/release.yml`
* **Exports (conceptual)**:

  * Job `pypi` that produces published artifacts
  * Trusted publishing via `id-token: write` and environment `pypi`

### Module: TestPyPI publish workflow

* **Maps to capability**: CI Publishing (TestPyPI)
* **Responsibility**: Build and publish to TestPyPI on demand.
* **File**: `.github/workflows/publish-testpypi.yml`
* **Exports (conceptual)**:

  * Workflow dispatch input `release_tag`
  * Publish step using `UV_PUBLISH_TOKEN` secret

### Module: Smoke test suite

* **Maps to capability**: CI smoke testing / Local install verification
* **Responsibility**: Assert artifacts can be installed and `lmstxt` is runnable.
* **File**: `tests/smoke_test.py` (referenced by CI)
* **Exports (conceptual)**:

  * `test_wheel_install_and_cli()`
  * `test_sdist_install_and_cli()`

### Module: Publishing runbook

* **Maps to capability**: Documentation & Operator Guidance
* **Responsibility**: One canonical procedure for releasing and troubleshooting.
* **File**: `docs/publishing.md` (new; can be derived from existing steps doc).

---

## 4) Dependency Chain (layers, explicit “Depends on: […]”)

### Foundation Layer

* **Packaging manifest (`pyproject.toml`)**: No dependencies.
* **Smoke test suite (`tests/smoke_test.py`)**: Depends on [Packaging manifest] (needs correct console script + package inclusion).

### CI Layer

* **TestPyPI workflow**: Depends on [Packaging manifest, Smoke test suite] (must build valid artifacts and have a verification story even if not enforced).
* **PyPI release workflow**: Depends on [Packaging manifest, Smoke test suite] (workflow gates publish on smoke tests).

### Documentation Layer

* **Publishing runbook**: Depends on [TestPyPI workflow, PyPI release workflow, Packaging manifest] (documents the actual system of record).

No cycles intended.

---

## 5) Development Phases (Phase 0…N; entry/exit criteria; tasks with dependencies + acceptance criteria + test strategy)

### Phase 0: Packaging correctness (foundation)

**Entry criteria**: Repository builds locally.

* **Task: Remove disallowed direct URL dependency** (depends on: none)

  * Acceptance criteria: No dependency strings contain `@ git+` (or other direct URL forms) in runtime deps.
  * Test strategy: Build artifacts + verify metadata acceptance via artifact validation step; confirm dependency resolves from PyPI. ([GitHub][1])

* **Task: Add explicit setuptools `src/` discovery config** (depends on: none)

  * Acceptance criteria: Built wheel contains `lmstudiotxt_generator` modules from `src/`.
  * Test strategy: Install wheel into isolated env; `python -c "import lmstudiotxt_generator"` succeeds; run `lmstxt --help`.

* **Task: Normalize dependency names to PyPI distributions** (depends on: none)

  * Acceptance criteria: All dependencies are installable from PyPI by canonical name (not local module name).
  * Test strategy: `pip install .` in a clean env succeeds without manual extra indexes; specifically ensure `llms-txt` resolves. ([PyPI][3])

**Exit criteria**: `python -m build` (or `uv build`) produces wheel+sdist that install and run the CLI locally.

**Delivers**: A PyPI-acceptable package configuration.

---

### Phase 1: Verification gates (smoke tests)

**Entry criteria**: Phase 0 complete.

* **Task: Implement/align `tests/smoke_test.py` for wheel + sdist** (depends on: [Phase 0 tasks])

  * Acceptance criteria: Smoke test can run against a wheel and an sdist and validates CLI entrypoint.
  * Test strategy: Execute smoke tests in isolation (mirroring CI approach) for both artifact types.

**Exit criteria**: Smoke tests pass locally and in CI context.

**Delivers**: Deterministic “is this releasable?” signal.

---

### Phase 2: CI publish workflows hardening

**Entry criteria**: Phase 1 complete.

* **Task: Align TestPyPI workflow naming, inputs, and secrets** (depends on: [Smoke tests])

  * Acceptance criteria: Workflow clearly targets this project; publishing to TestPyPI works for a specified ref/tag.
  * Test strategy: Manual dispatch in a test branch; confirm artifacts appear on TestPyPI and can be installed from that index.

* **Task: Confirm PyPI trusted publishing configuration matches workflow** (depends on: [Smoke tests])

  * Acceptance criteria: Tag push triggers publish without stored API token; workflow uses OIDC (`id-token: write`) and configured PyPI Trusted Publisher.  ([PyPI Docs][2])
  * Test strategy: Dry-run by building/tagging in a non-production setting (or use TestPyPI trusted publisher if configured).

**Exit criteria**: Both workflows succeed end-to-end with required gates.

**Delivers**: Automated releases.

---

### Phase 3: Operator documentation

**Entry criteria**: Phase 2 complete.

* **Task: Consolidate runbook** (depends on: [Phase 2 tasks])

  * Acceptance criteria: One doc covers: local preflight, TestPyPI publish, PyPI publish via tag, troubleshooting common failures (metadata rejection, missing packages, CLI missing).
  * Test strategy: “Docs test” checklist: a new maintainer follows doc in a fresh clone and reaches a successful TestPyPI publish.

**Exit criteria**: Document is the source of truth; links to CI workflows included.

**Delivers**: Reduced maintainer friction and fewer release regressions.

---

## 6) User Experience

### Personas

* **Release maintainer**: wants a single command/path (“push tag”) with confidence gates.
* **Contributor**: wants packaging changes to be testable in PR without secrets access.

### Key flows

1. **Preflight (local)**: build → validate → install artifact → run `lmstxt --help`.
2. **TestPyPI**: workflow dispatch with `release_tag` → publish to TestPyPI → install from TestPyPI → run CLI.
3. **PyPI release**: push `vX.Y.Z` tag → CI builds + smoke tests → trusted publish → post-install verification.  ([PyPI Docs][2])

UX notes (non-UI system):

* Failures must be actionable: CI should clearly indicate whether failure is build, smoke test, or publish/auth.

---

## 7) Technical Architecture

### Components

* **Build backend**: `setuptools.build_meta` per `pyproject.toml`.
* **Build/publish runner**: `uv build` and `uv publish` in CI.
* **Authentication**:

  * PyPI: Trusted publishing using OIDC token exchange (GitHub Actions `id-token: write`).  ([PyPI Docs][2])
  * TestPyPI: Token secret currently (`TEST_PYPI_TOKEN`), optionally upgradable to trusted publishing if desired.

### Data models (release context)

* **Artifacts**: `{wheel, sdist}` produced into `dist/`.
* **Release identifier**: Git tag `vX.Y.Z` mapped to package version.

### Key decisions

* **Use trusted publishing for PyPI**

  * Rationale: Eliminates long-lived credentials; aligns with PyPI recommended approach. ([PyPI Docs][2])
  * Trade-offs: Requires PyPI Trusted Publisher setup per repo/environment.
  * Alternatives: API tokens via secrets.

---

## 8) Test Strategy

### Test pyramid targets

* Unit tests: existing project tests (out of scope here except ensuring they run pre-release).
* Integration tests: **artifact install + CLI smoke tests** are mandatory gates for release.
* End-to-end: TestPyPI publish + install from TestPyPI (manual or optional scheduled).

### Coverage minimums (release-critical)

* Smoke tests must cover:

  * Install wheel → import package → run `lmstxt --help`.
  * Install sdist → import package → run `lmstxt --help`.
  * (Optional) Minimal runtime invocation that doesn’t require LM Studio connectivity.

### Critical scenarios

* **Direct URL dependency present** → publish rejected (must be caught before publish). ([GitHub][1])
* **Package not included in wheel** (`src/` discovery missing) → import fails after install.
* **Console script missing** → `lmstxt` not found.

---

## 9) Risks and Mitigations

### Risk: PyPI rejects metadata (invalid `Requires-Dist`)

* **Impact**: High
* **Likelihood**: High given current VCS dependency.
* **Mitigation**: Block direct URL dependencies; preflight artifact validation. ([GitHub][1])
* **Fallback**: Temporary pin to released dependency versions on PyPI; use TestPyPI to validate before main release.

### Risk: “Empty” distribution due to `src/` discovery misconfig

* **Impact**: High
* **Likelihood**: Medium
* **Mitigation**: Add explicit setuptools config; enforce smoke test that imports after install.
* **Fallback**: Fail release workflow on import/CLI failure.

### Risk: Trusted publisher misconfiguration blocks releases

* **Impact**: Medium
* **Likelihood**: Medium
* **Mitigation**: Document setup; include clear CI error messaging; validate environment `pypi` exists.  ([PyPI Docs][2])
* **Fallback**: Use API token publishing (least preferred) until configuration corrected.

---

## 10) Appendix

### Source materials (provided)

* `pyproject.toml` (project metadata, deps, CLI entrypoint).
* `release.yml` (tag-based publish w/ smoke tests + `uv publish`).
* `publish-testpypi.yml` (manual TestPyPI publish using token secret).
* Local publishing steps doc (runbook seed).
* Source layout and package structure under `src/`.

### External references (constraints)

* PyPI Trusted Publishing (OIDC). ([PyPI Docs][2])
* Direct URL dependency rejection examples/discussion. ([GitHub][1])
* `llms-txt` distribution exists on PyPI (name normalization). ([PyPI][3])

### Open questions

* Should TestPyPI also use trusted publishing (OIDC) instead of a long-lived token secret?
* What is the desired versioning source of truth: tag-only, or `pyproject.toml` version bump + tag consistency enforcement?

[1]: https://github.com/pypa/pip/issues/6301?utm_source=chatgpt.com "Allow direct urls in install_requires · Issue #6301 · pypa/pip"
[2]: https://docs.pypi.org/trusted-publishers/?utm_source=chatgpt.com "Publishing to PyPI with a Trusted Publisher"
[3]: https://pypi.org/project/llms-txt/?utm_source=chatgpt.com "llms-txt"
