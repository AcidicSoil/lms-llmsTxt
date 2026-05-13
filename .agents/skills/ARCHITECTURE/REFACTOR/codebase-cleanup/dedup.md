# Deduplication and Import Rewrite

Run import rewrites before deleting anything. Verify full test suite after rewrites, before deletes.

## Import Rewrite Procedure

### 1. Generate the rewrite map

From the classification table, build an explicit old → canonical mapping:

| Old import | Canonical import |
|------------|-----------------|
| `pkg.config` | `pkg.core.config` |
| `pkg.curation` | `pkg.ingestion.curation` |
| `pkg.runtime_registry` | `pkg.runtime.registry` |
| `pkg.pswg_deepagent` | `pkg.integrations.pswg_deepagent` |

### 2. Find all affected files

```bash
rg -n "from pkg\.(config|curation|execution|runtime_registry|pswg_deepagent)" pkg tests
rg -n "import pkg\.(config|curation|execution|runtime_registry|pswg_deepagent)" pkg tests
```

### 3. Rewrite imports

```python
# before
from pkg.config import load_config
from pkg.pswg_deepagent.agent import build_agent

# after
from pkg.core.config import load_config
from pkg.integrations.pswg_deepagent.agent import build_agent
```

### 4. Verify before deleting

```bash
uv run pytest
rg -n "from pkg\.(config|curation|execution|runtime_registry|pswg_deepagent)" pkg tests
# must return zero matches
```

## Deleting Stale Copies

Only after import rewrites pass:

```bash
# Delete stale duplicate package
rm -rf pkg/duplicate_package/

# Delete root shim files
rm pkg/config.py pkg/curation.py pkg/execution.py pkg/runtime_registry.py
```

## Import Identity Tests (for duplicate packages)

Add before deleting the stale copy to verify canonical resolution:

```python
# tests/test_<module>_import_compat.py
import importlib

def test_submodules_resolve_to_canonical() -> None:
    submodules = ["agent", "schemas", "run"]
    for name in submodules:
        legacy = importlib.import_module(f"pkg.old_package.{name}")
        canonical = importlib.import_module(f"pkg.integrations.new_package.{name}")
        assert legacy is canonical
```

Run after rewrite, before delete:

```bash
uv run pytest tests/test_<module>_import_compat.py
```

After delete, these tests should still pass (canonical path only) — update assertions accordingly.

## Runtime Asset Check

If the canonical package contains runtime assets (prompts, templates, data files), verify packaging:

```python
from importlib import resources

def test_runtime_assets_are_packaged() -> None:
    assets = resources.files("pkg.integrations.new_package").joinpath("assets")
    assert assets.joinpath("main.md").is_file()
```
