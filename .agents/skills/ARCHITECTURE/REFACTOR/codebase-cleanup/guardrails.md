# Architecture Guardrails

Add these tests after cleanup to prevent regression. Shrink allowlists as migration progresses.

## 1. Root Layout Allowlist

Fails if any new file appears at package root outside the allowed set.

```python
# tests/test_architecture_root_layout.py
from pathlib import Path

ALLOWED_ROOT_FILES = {
    "__init__.py",
    "__main__.py",
    "cli.py",
    "py.typed",
}

def test_root_contains_only_allowed_files() -> None:
    root = Path("pkg")
    actual = {p.name for p in root.iterdir() if p.is_file()}
    assert actual <= ALLOWED_ROOT_FILES, f"Unexpected root files: {actual - ALLOWED_ROOT_FILES}"
```

During migration, extend with a tracked compat allowlist and shrink it PR by PR:

```python
COMPAT_ALLOWLIST = {
    "config.py",    # remove after PR 3
    "models.py",    # remove after PR 3
}

def test_root_contains_only_allowed_files() -> None:
    root = Path("pkg")
    actual = {p.name for p in root.iterdir() if p.is_file()}
    assert actual <= ALLOWED_ROOT_FILES | COMPAT_ALLOWLIST
```

## 2. No Duplicate Package

Fails if the deleted stale package directory re-appears.

```python
# tests/test_no_duplicate_packages.py
from pathlib import Path

def test_stale_package_does_not_exist() -> None:
    assert not Path("pkg/old_package").exists()
```

## 3. Import Boundary Test

AST-scans all source files; fails if any forbidden old import path is used.

```python
# tests/test_import_boundaries.py
import ast
from pathlib import Path

FORBIDDEN_IMPORTS = {
    "pkg.config",
    "pkg.constants",
    "pkg.curation",
    "pkg.execution",
    "pkg.runtime_registry",
    "pkg.pswg_deepagent",
    # extend as old paths are removed
}

SKIP = {".venv", ".git", "dist", "build"}

def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            out.add(node.module)
    return out

def test_no_forbidden_legacy_imports() -> None:
    offenders: dict[str, list[str]] = {}
    for path in Path(".").rglob("*.py"):
        if any(p in SKIP for p in path.parts):
            continue
        hits = sorted(_imports(path) & FORBIDDEN_IMPORTS)
        if hits:
            offenders[str(path)] = hits
    assert offenders == {}, offenders
```

## 4. No Deprecated Symbol Export

Fails if a removed callable re-appears in the public surface.

```python
# tests/test_no_deprecated_exports.py
import pkg

FORBIDDEN_EXPORTS = {"deprecated_cli", "codefetch_plan_cli"}

def test_no_deprecated_symbols_exported() -> None:
    exported = set(getattr(pkg, "__all__", [])) | set(vars(pkg))
    leaked = exported & FORBIDDEN_EXPORTS
    assert not leaked, f"Deprecated symbols still exported: {leaked}"
```

## Running All Guardrails

```bash
uv run pytest tests/test_architecture_root_layout.py \
               tests/test_no_duplicate_packages.py \
               tests/test_import_boundaries.py \
               tests/test_no_deprecated_exports.py \
               -v
```

Add this as a separate CI step so architecture failures are clearly labeled.
