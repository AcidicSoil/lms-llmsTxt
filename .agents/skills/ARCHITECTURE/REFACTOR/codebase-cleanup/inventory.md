# Inventory and Classification

Classify every file before moving or deleting anything. Acceptance criterion: every file has exactly one label.

## Labels

| Label | Definition | Action |
|-------|------------|--------|
| `entrypoint` | `__init__.py`, `__main__.py`, package-level init | Keep |
| `public_facade` | Intentionally stable public surface (e.g. `cli.py`) | Keep, possibly trim |
| `compat_shim` | Proxies to a canonical module; no real implementation | Delete after import rewrite |
| `legacy_impl` | Real implementation that belongs in a domain package | Move, then delete root copy |
| `duplicate_package` | Full package that duplicates another location | Designate canonical, delete stale |
| `deprecated_entrypoint` | CLI binary launcher or callable with a removal warning | Remove from source and packaging |
| `unknown` | Not yet classified — do not touch | Investigate before labeling |

## Classification Table Template

Produce this table for the target package before any changes:

| File | Label | Canonical Destination |
|------|-------|-----------------------|
| `__init__.py` | `entrypoint` | stay |
| `__main__.py` | `entrypoint` | stay |
| `cli.py` | `public_facade` | stay |
| `config.py` | `compat_shim` | `core/config.py` |
| `constants.py` | `compat_shim` | `core/constants.py` |
| `legacy.py` | `legacy_impl` | `integrations/oracle/runtime.py` |
| `pswg_deepagent/` | `duplicate_package` | `integrations/pswg_deepagent/` |
| `codefetch_plan` | `deprecated_entrypoint` | delete |

## Usage Scan Commands

```bash
# All root-level files
find <pkg> -maxdepth 1 -type f | sort

# All root-level directories
find <pkg> -maxdepth 1 -type d | sort

# References to a suspected shim path
rg -n "from <pkg>\.<module>" <pkg> tests docs

# References to a suspected duplicate package
rg -rn "<pkg>\.<dup_package>" <pkg> tests
```

## Designating the Canonical Copy (Duplicates)

Prefer the copy that:
1. Lives under the correct architectural boundary (e.g. `integrations/`, `core/`)
2. Has more complete contents (runtime assets, prompt files, etc.)
3. Is referenced by more internal imports already
4. Has been touched more recently in git history

```bash
git log --oneline -- <pkg>/dup_package/ | head -5
git log --oneline -- <pkg>/integrations/dup_package/ | head -5
diff -rq <pkg>/dup_package/ <pkg>/integrations/dup_package/
```
