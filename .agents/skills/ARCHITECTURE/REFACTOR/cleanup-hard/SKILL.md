---
name: cleanup-hard
description: "Hard codebase cleanup for any language or project: eliminate shim files, consolidate duplicate modules/packages, remove deprecated entrypoints, and add guardrail tests to prevent regression. No compatibility layer — canonical paths only. WHEN: \"clean up root files\", \"remove shims\", \"consolidate duplicates\", \"remove deprecated command\", \"flat layout cleanup\", \"canonical imports\", \"eliminate compat layer\", \"architecture guardrails\", \"hard cleanup\", \"no shims\", \"remove legacy module\"."
license: MIT
metadata:
  author: relayforge
  version: "1.0.0"
---

# Hard Cleanup

Eliminate shims, duplicates, and deprecated entrypoints across any language or project.
No compatibility layer. Canonical paths only. Guardrail tests hold the line.

## Placeholders

Before starting, resolve these for the target project:

| Placeholder | Meaning | Example |
|-------------|---------|---------|
| `<PKG_ROOT>` | Root of the module/package tree | `src/`, `lib/`, `relayforge/` |
| `<TEST_CMD>` | Test runner invocation | `pytest`, `jest`, `go test ./...` |
| `<SCAN_CMD>` | Code search tool | `rg`, `grep -r`, `git grep` |
| `<BUILD_CMD>` | Build/compile step | `uv build`, `npm run build`, `go build` |
| `<INSTALL_CMD>` | Install and verify step | `pip install dist/*.whl`, `npm install` |
| `<PACKAGING_CONFIG>` | Project manifest | `pyproject.toml`, `package.json`, `Cargo.toml` |
| `<SEP>` | Module path separator | `.` (Python), `/` (Go/JS), `::` (Rust) |
| `<OLD_PATH>` | Stale module/import path being removed | `pkg.config`, `src/shims/auth` |
| `<CANONICAL_PATH>` | Correct destination path | `pkg.core.config`, `src/core/auth` |
| `<BINARY_NAME>` | Deprecated CLI binary or command | `old-tool`, `codefetch_plan` |
| `<CANONICAL_CMD>` | Replacement canonical command | `new-tool`, `relayforge` |

## Execution Policy

Ambiguity > 0.2 → one blocking question before proceeding.
Execute in PR sequence. Never big-bang. Verify between each PR.

## Workflow

### 1. Inventory — classify every file

Run scans before touching anything. Every file gets one label. No file stays `unknown`.

See [Inventory and Classification](references/inventory.md).

### 2. Resolve duplicates

Designate canonical. Rewrite all references. Delete stale copy. Add identity tests.

See [Deduplication and Reference Rewrite](references/dedup.md).

### 3. Remove deprecated entrypoints

Remove from source, packaging config, and docs. Add no-symbol tests.

See [Deprecated Entrypoint Removal](references/deprecated.md).

### 4. Add guardrails

Add tests that fail CI if cleanup is undone.

See [Architecture Guardrails](references/guardrails.md).

## PR Sequence

| PR | Changes | Verification |
|----|---------|--------------|
| 1 | Reference rewrites only — no deletes | `<TEST_CMD>` passes; zero hits from `<SCAN_CMD>` for `<OLD_PATH>` |
| 2 | Delete duplicate modules/packages, add identity tests | `<TEST_CMD>` passes |
| 3 | Delete root shim files, add root allowlist + import boundary tests | `<TEST_CMD>` + guardrail tests pass |
| 4 | Move misplaced domain files (CLI handlers, legacy modules, etc.) | Smoke-test CLI entrypoints |
| 5 | Remove `<BINARY_NAME>` from `<PACKAGING_CONFIG>` and source | Build from manifest, verify `<BINARY_NAME>` absent; `<CANONICAL_CMD> --help` works |

## Constraints

- Never delete before reference rewrites are verified
- Never introduce a compat shim — hard delete only
- If the project is published and externally consumed: semver-major release required
- Run `<TEST_CMD>` after each PR before merging
