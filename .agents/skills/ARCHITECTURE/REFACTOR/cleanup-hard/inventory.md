# Inventory and Classification

Classify every file before moving or deleting. Acceptance criterion: every file has exactly one label. No `unknown` remains.

## Labels

| Label | Definition | Action |
|-------|------------|--------|
| `entrypoint` | Package/module init, main entry (e.g. `__init__`, `index`, `main`) | Keep |
| `public_facade` | Intentionally stable public surface (e.g. `cli`, `api`) | Keep; trim if bloated |
| `compat_shim` | Re-exports or proxies to a canonical module; no real implementation | Delete after reference rewrite |
| `legacy_impl` | Real implementation that belongs in a domain module | Move to domain, then delete root copy |
| `duplicate_module` | Duplicates another module or package at a different path | Designate canonical, delete stale |
| `deprecated_entrypoint` | CLI binary, callable, or command with a removal notice | Remove from source and packaging config |
| `unknown` | Not yet classified — do not touch | Investigate before labeling |

## Classification Table Template

Produce this table for `<PKG_ROOT>` before any changes:

| Path | Label | Canonical Destination |
|------|-------|-----------------------|
| `<PKG_ROOT>/index.<ext>` | `entrypoint` | stay |
| `<PKG_ROOT>/cli.<ext>` | `public_facade` | stay |
| `<PKG_ROOT>/config.<ext>` | `compat_shim` | `<PKG_ROOT>/core/config.<ext>` |
| `<PKG_ROOT>/legacy.<ext>` | `legacy_impl` | `<PKG_ROOT>/integrations/oracle/runtime.<ext>` |
| `<PKG_ROOT>/old_module/` | `duplicate_module` | `<PKG_ROOT>/domain/new_module/` |
| `<PKG_ROOT>/old-binary` | `deprecated_entrypoint` | delete |

## Scan Commands

```bash
# List all root-level files
find <PKG_ROOT> -maxdepth 1 -type f | sort

# List all root-level directories
find <PKG_ROOT> -maxdepth 1 -type d | sort

# Find references to a suspected shim or old path
<SCAN_CMD> -rn "<OLD_PATH>" <PKG_ROOT> tests docs

# Find references to a suspected duplicate module
<SCAN_CMD> -rn "<PKG_ROOT><SEP><DUPLICATE_MODULE>" <PKG_ROOT> tests
```

## Designating the Canonical Copy

When two modules/packages contain the same implementation, prefer the copy that:

1. Lives under the correct architectural boundary (`core/`, `integrations/`, `domain/`)
2. Has more complete contents (runtime assets, templates, config)
3. Is referenced by more internal imports already
4. Has more recent changes in version history

```bash
# Compare modification history
git log --oneline -- <PKG_ROOT>/old_module/ | head -5
git log --oneline -- <PKG_ROOT>/domain/new_module/ | head -5

# Diff to surface divergence
diff -rq <PKG_ROOT>/old_module/ <PKG_ROOT>/domain/new_module/
```

Resolve any divergence before declaring the canonical. Do not delete without byte-level confirmation that no unique implementation exists in the stale copy.
