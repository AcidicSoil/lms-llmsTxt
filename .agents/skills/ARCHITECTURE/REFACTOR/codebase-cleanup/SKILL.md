---
name: codebase-cleanup
description: "Hard codebase cleanup: eliminate shim files, consolidate duplicate packages, remove deprecated entrypoints, and add architecture tests to prevent regression. No compatibility layer — canonical paths only. WHEN: \"clean up root files\", \"remove shims\", \"consolidate duplicate packages\", \"remove deprecated binary\", \"flat architecture cleanup\", \"canonical imports\", \"eliminate compat layer\", \"architecture guardrails\", \"hard cleanup\", \"no shims\"."
license: MIT
metadata:
  author: relayforge
  version: "1.0.0"
---

# Codebase Hard Cleanup

Eliminate shims, duplicates, and deprecated entrypoints. No compatibility layer — canonical paths only. Add architecture tests to hold the line.

## When to Use

- Root directory has accumulated loose files from incomplete refactors
- Two packages or modules contain the same implementation
- A deprecated CLI binary or callable symbol still exists in source
- Internal imports still reference old paths that were moved

## Execution Policy

Ambiguity > 0.2 → ask one blocking question before proceeding.
Execute in PR sequence. Never big-bang. Verify between PRs.

## Workflow

### 1. Inventory — classify every file

Run a usage scan before touching anything:

```bash
# List all root-level files
find <package_root> -maxdepth 1 -type f | sort

# Find all internal imports referencing old paths
rg -n "from <pkg>\.(old_module|shim_module|legacy_module)" <package_root> tests
```

Classify every root file into one label. No file stays "unknown."

See [Inventory and Classification](references/inventory.md) for labels and classification table.

### 2. Resolve duplicates and canonicalize

For each duplicate package or module:
1. Designate canonical (prefer the one with more complete contents, correct domain boundary, runtime assets)
2. Rewrite all internal imports to canonical path
3. Delete the stale copy
4. Add import identity tests

See [Deduplication and Import Rewrite](references/dedup.md).

### 3. Remove deprecated entrypoints

For each deprecated CLI binary or callable symbol:
1. Remove from packaging config (`pyproject.toml`, `setup.cfg`)
2. Remove callable from source
3. Replace all doc/example references with canonical name
4. Add tests asserting the old symbol/name is gone

See [Deprecated Entrypoint Removal](references/deprecated.md).

### 4. Add architecture guardrails

Add tests that fail fast if cleanup is undone:
- Root allowlist — new root files fail CI
- No-duplicate assertion — stale package path must not exist
- Import boundary test — forbidden old import paths fail AST scan
- No-legacy-symbol test — removed callables must not be re-exported

See [Architecture Guardrails](references/guardrails.md).

## PR Sequence

| PR | Changes | Verification |
|----|---------|--------------|
| 1 | Import rewrites only, no deletes | Full test suite passes |
| 2 | Delete duplicate packages, add identity tests | Full test suite passes |
| 3 | Delete root shim files, add root allowlist + import boundary tests | Full test suite + arch tests pass |
| 4 | Move misplaced domain files (CLI, legacy, etc.) | Smoke-test CLI entrypoints |
| 5 | Remove deprecated binary from packaging + source | Install from wheel, verify binary absent |

## Constraints

- Never delete before import rewrites are verified
- Never add a compat shim — hard delete only
- If package is published externally: semver-major release required
- Run `uv run pytest` after each PR before merging
