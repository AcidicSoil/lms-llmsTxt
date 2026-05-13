# Deprecated Entrypoint Removal

Covers: CLI binaries, callable symbols, console script entries, command aliases, exported functions with deprecation warnings.

## Removal Checklist

- [ ] Locate all definitions and re-exports of `<BINARY_NAME>` / deprecated callable
- [ ] Remove callable from source
- [ ] Remove from any public export list (`__all__`, `index`, `mod.rs`, barrel file)
- [ ] Remove script/binary entry from `<PACKAGING_CONFIG>`
- [ ] Replace all doc and example references with `<CANONICAL_CMD>`
- [ ] Add tests asserting the symbol and command name are gone
- [ ] Verify by building and installing from manifest

## 1. Find all definitions and references

```bash
<SCAN_CMD> -rn "<BINARY_NAME>\|<BINARY_NAME_SLUG>" \
    <PKG_ROOT> tests docs \
    <PACKAGING_CONFIG>
```

## 2. Remove from source

Locate the deprecated callable (function, method, exported symbol) and delete it entirely.
Also remove it from any export list or barrel file.

```
# before
exports: [canonical_fn, deprecated_fn]

# after
exports: [canonical_fn]
```

Remove any wrapper that forwards to `<CANONICAL_CMD>` with a deprecation message — do not keep it as a quiet alias.

## 3. Remove from packaging config

```
# <PACKAGING_CONFIG> — before
[scripts / bin / commands]
<CANONICAL_CMD> = "<PKG_ROOT>:<canonical_fn>"
<BINARY_NAME>   = "<PKG_ROOT>:<deprecated_fn>"

# <PACKAGING_CONFIG> — after
[scripts / bin / commands]
<CANONICAL_CMD> = "<PKG_ROOT>:<canonical_fn>"
```

Common locations by ecosystem:

| Ecosystem | Config file | Key |
|-----------|-------------|-----|
| Python | `pyproject.toml` | `[project.scripts]` |
| Node.js | `package.json` | `"bin"` |
| Go | `cmd/<name>/main.go` | delete the cmd directory |
| Rust | `Cargo.toml` | `[[bin]]` |
| Shell | `Makefile` / install script | delete the install target |

## 4. Update docs and examples

```bash
# Find remaining references
<SCAN_CMD> -rn "<BINARY_NAME>" docs README* .

# Replace: before → after
# <BINARY_NAME> run ...  →  <CANONICAL_CMD> run ...
```

## 5. Verify by install

```bash
<BUILD_CMD>
<INSTALL_CMD>

<CANONICAL_CMD> --help    # must succeed
<BINARY_NAME> --help      # must fail (command not found / unknown command)
```

Do not rely on executing `<BINARY_NAME>` in CI to confirm removal — a stale global binary on `PATH` causes false negatives. Verify through the manifest and source symbol checks instead.

## No-Symbol Test Pattern

```
# Pseudocode — adapt to language test framework
import_root_module()
assert <deprecated_callable> not in public_exports()
assert <deprecated_callable> not in dir(root_module)
```

## No-Reference Test Pattern (optional)

Scope to `<PKG_ROOT>` and `tests/` only. Exclude changelog and release notes if they legitimately document the removal.

```
# Pseudocode
forbidden_terms = ["<BINARY_NAME>", "<BINARY_NAME_SLUG>"]
scan_paths = ["<PKG_ROOT>", "tests"]
skip_paths = [".git", "dist", "build", "CHANGELOG"]

for each file in scan_paths (recursive, skip skip_paths):
    for each term in forbidden_terms:
        assert term not in file_contents
```
