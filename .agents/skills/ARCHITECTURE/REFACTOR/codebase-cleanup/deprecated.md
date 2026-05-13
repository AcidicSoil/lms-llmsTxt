# Deprecated Entrypoint Removal

Covers: CLI binaries, callable symbols, console script entries, and any `deprecated_name` warning wrapper.

## Removal Checklist

- [ ] Remove callable from source (`__init__.py` or wherever defined)
- [ ] Remove from `__all__` in source
- [ ] Remove script entry from packaging config
- [ ] Replace all doc/example references with canonical name
- [ ] Add tests asserting the symbol and binary name are gone

## 1. Remove from source

Find the deprecated callable:

```bash
rg -n "deprecated_name|old_binary_name|codefetch_plan_cli" pkg tests docs pyproject.toml
```

Edit `pkg/__init__.py`:

```python
# before
__all__ = ["main", "canonical_cli", "deprecated_cli"]

def deprecated_cli() -> None:
    raise SystemExit(_run_cli(sys.argv[1:], deprecated_name="old-binary"))

# after
__all__ = ["main", "canonical_cli"]
# deprecated_cli deleted entirely
```

## 2. Remove from packaging config

`pyproject.toml`:

```toml
# before
[project.scripts]
canonical-tool = "pkg:canonical_cli"
old-tool = "pkg:deprecated_cli"

# after
[project.scripts]
canonical-tool = "pkg:canonical_cli"
```

Also check `setup.cfg` and `setup.py` for `entry_points` / `console_scripts`.

## 3. Update docs and examples

```bash
# Find all references
rg -rn "old-tool|old_binary|deprecated_name" docs README* .

# Replace in docs
# before: old-tool run ...
# after:  canonical-tool run ...
```

## 4. Verify by install

```bash
uv build
uv run python -m pip install --force-reinstall dist/*.whl
canonical-tool --help          # must work
old-tool --help                # must fail: command not found
```

Do not test `old-tool` execution in CI — a stale global binary on PATH causes false negatives. Test the package symbol directly instead.

## No-Symbol Tests

```python
# tests/test_no_deprecated_<name>.py
import pkg

def test_deprecated_callable_not_exported() -> None:
    assert not hasattr(pkg, "deprecated_cli")
    assert "deprecated_cli" not in getattr(pkg, "__all__", [])
```

## No-Reference Test (optional, scope carefully)

```python
from pathlib import Path

FORBIDDEN = {"old_binary_name", "old-binary-name"}
SCAN_DIRS = {"pkg", "tests"}
SKIP_DIRS = {".git", ".venv", "dist", "build"}

def test_no_deprecated_name_references() -> None:
    offenders: dict[str, list[str]] = {}
    for path in Path(".").rglob("*"):
        if path.is_dir() or any(p in SKIP_DIRS for p in path.parts):
            continue
        if path.suffix not in {".py", ".toml", ".md", ".rst", ".txt", ".yaml", ".yml"}:
            continue
        if str(path.parent) not in SCAN_DIRS and not any(str(path).startswith(d) for d in SCAN_DIRS):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        hits = sorted(t for t in FORBIDDEN if t in text)
        if hits:
            offenders[str(path)] = hits
    assert offenders == {}
```

Scope to `pkg/` and `tests/` only if changelog/history files legitimately mention the old name.
