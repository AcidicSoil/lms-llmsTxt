# Dependency security posture review

## Detected ecosystems
- Python project management and locking: `uv` via `pyproject.toml` + committed `uv.lock`
- JavaScript package management: `pnpm` is the declared package manager at the repo root (`packageManager` in root `package.json`) with committed `pnpm-lock.yaml` at both root and `hypergraph/`
- JavaScript script execution still occurs via both `pnpm` and `npm --prefix hypergraph ...` wrapper scripts at the root

## Repository-level config inspected
- Present:
  - `pyproject.toml`
  - `uv.lock`
  - `package.json`
  - `pnpm-lock.yaml`
  - `hypergraph/package.json`
  - `hypergraph/pnpm-lock.yaml`
  - `.github/workflows/release.yml`
  - `.github/workflows/publish-testpypi.yml`
- Absent:
  - `.npmrc`
  - `hypergraph/.npmrc`
  - `pnpm-workspace.yaml`
  - `uv.toml`
  - `.nvmrc`
  - `.node-version`

## AGENTS-style conflict report

Dependency security posture conflicts detected

- Ecosystem: mixed (`uv` for Python, `pnpm`/`npm` for JavaScript)
- Enforcement scope: mixed
- Blocking conflicts:
  - `hypergraph/package.json`: dependencies are mostly semver ranges (`^...`) and there is no repo-level `save-exact` policy, so future add/update operations can widen drift from the reviewed baseline.
  - `package.json`: root declares `packageManager = pnpm@10.29.2+sha512...`, but root scripts still invoke `npm --prefix hypergraph ...`, which weakens package-manager-specific policy enforcement for the HyperGraph app.
  - repo scope: no committed `.npmrc` or `pnpm-workspace.yaml`, so script execution, engine enforcement, freshness quarantine, and provenance/trust controls are not enforced at repo level for teammates or CI.
  - `hypergraph/package.json`: no `packageManager` field and no `engines` declaration, so runtime/package-manager expectations are not self-declared in the app package.
- Redundant controls:
  - none currently; the bigger problem is missing repo-enforced controls rather than overlapping ones.
- Missing controls:
  - repo scope: repo-enforced JavaScript install policy (`.npmrc` and/or `pnpm-workspace.yaml`)
  - repo scope: script approval policy (`onlyBuiltDependencies` / `ignoredBuiltDependencies`) for packages needing install-time scripts
  - repo scope: freshness quarantine (`minimumReleaseAge`) for new JS releases
  - repo scope: trust/provenance policy (`trustPolicy`, `blockExoticSubdeps`) for JS installs
  - repo scope: engine/runtime declaration for Node/pnpm in `hypergraph/package.json`
  - CI scope: locked/frozen install checks rather than relying on ad hoc local state
- Operational risk:
  - a teammate or CI job can recreate the JavaScript dependency tree without repo-enforced quarantine, script restrictions, or engine checks, and root wrapper scripts may bypass the intended pnpm-centric posture.
- Required remediation:
  1. Standardize JS package-manager usage on `pnpm` for the HyperGraph app and remove `npm --prefix hypergraph ...` wrappers or replace them with `pnpm --dir hypergraph ...`.
  2. Add repo-level JS install policy (`.npmrc` and/or `pnpm-workspace.yaml`) with exact-save and engine enforcement at minimum.
  3. Add pnpm-native supply-chain controls where compatible with the repo: `minimumReleaseAge`, `trustPolicy`, and `blockExoticSubdeps`.
  4. Introduce explicit build-script approval for dependencies that require install-time scripts before enabling a default-deny script posture.
  5. Keep using committed lockfiles and run locked/frozen verification paths in CI for both ecosystems.

## Current posture by control category
- Freshness quarantine:
  - Python/uv: no repo-level quarantine control found.
  - JavaScript/pnpm: absent in repo config.
- Script execution control:
  - Python/uv: no additional repo-level restriction found.
  - JavaScript/pnpm: absent in repo config; no allowlist/denylist committed.
- Deterministic resolution:
  - Python/uv: good baseline (`uv.lock` committed).
  - JavaScript/pnpm: good baseline (`pnpm-lock.yaml` committed), but enforcement path is weakened by mixed `npm` wrappers and missing repo config.
- Provenance/source restrictions:
  - Python/uv: no repo-level restrictions found.
  - JavaScript/pnpm: absent in repo config.
- Exactness and drift reduction:
  - Python: now pinned in `pyproject.toml`.
  - JavaScript: absent at repo-policy level; manifests still use ranges.
- Engine/runtime enforcement:
  - Python: `requires-python >=3.10` present.
  - JavaScript: absent at repo-policy level.
- Pre-run dependency verification:
  - Python/uv: partial strength because `uv run` auto-locks and syncs, but CI is not consistently using `--locked`/`--frozen`.
  - JavaScript/pnpm: no repo-level pre-run dependency verification found.
