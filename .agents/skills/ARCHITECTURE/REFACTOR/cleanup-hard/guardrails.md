# Architecture Guardrails

Add these after cleanup. Each test encodes one structural rule that CI enforces permanently. Shrink allowlists as migration progresses — never expand them.

## Guardrail 1 — Root Layout Allowlist

**Rule:** No new files may appear at `<PKG_ROOT>` root outside the declared allowed set.

```
# Pseudocode — implement in project's test framework
ALLOWED_ROOT_FILES = {
    "<entrypoint_file>",      # e.g. __init__.py, index.ts, main.go
    "<main_file>",            # e.g. __main__.py, cmd/main.go
    "<public_cli_file>",      # e.g. cli.py, cli.ts
    "<type_marker>",          # e.g. py.typed, go.sum
}

test "root contains only allowed files":
    actual = files_at(<PKG_ROOT>, depth=1)
    unexpected = actual - ALLOWED_ROOT_FILES
    assert unexpected is empty
```

**During migration:** add a tracked `COMPAT_ALLOWLIST` for files not yet moved, and remove entries PR by PR:

```
COMPAT_ALLOWLIST = {
    "config.<ext>",     # remove after PR 3
    "models.<ext>",     # remove after PR 3
}

actual <= ALLOWED_ROOT_FILES | COMPAT_ALLOWLIST
```

## Guardrail 2 — No Duplicate Module

**Rule:** The deleted stale module path must not exist.

```
# Pseudocode
test "stale module path does not exist":
    assert path_does_not_exist("<PKG_ROOT>/old_module/")
    assert path_does_not_exist("<PKG_ROOT>/<DUPLICATE_MODULE>/")
```

One assertion per removed duplicate. Add a new one each time a stale module is deleted.

## Guardrail 3 — Import Boundary

**Rule:** No source file may reference a forbidden old import path.

Implementation approach depends on language:

**Grep-based (works in any language):**

```bash
# Fail if any source file contains a forbidden path
<SCAN_CMD> -rn \
  "<OLD_PATH_1>\|<OLD_PATH_2>\|<OLD_PATH_3>" \
  <PKG_ROOT> tests \
  && exit 1 || exit 0
```

Wire this as a CI step or a test that shells out:

```
test "no forbidden legacy import paths":
    result = shell("<SCAN_CMD> -rn '<OLD_PATH_1>|<OLD_PATH_2>' <PKG_ROOT> tests")
    assert result.matches == 0
```

**Language-specific approaches:**

| Language | Approach |
|----------|----------|
| Python | AST walk `import` / `from` nodes; check `node.module` against forbidden set |
| TypeScript/JS | AST parse `import` / `require` strings; check against forbidden prefixes |
| Go | Parse `import` blocks; reject forbidden module paths |
| Rust | Parse `use` statements; reject forbidden crate paths |
| Any | `<SCAN_CMD>` grep in CI — simple and cross-language |

**FORBIDDEN_IMPORTS set template:**

```
FORBIDDEN_IMPORTS = [
    "<PKG_ROOT><SEP>config",
    "<PKG_ROOT><SEP>constants",
    "<PKG_ROOT><SEP>old_module",
    "<PKG_ROOT><SEP><DUPLICATE_MODULE>",
    # extend as old paths are confirmed removed
]
```

## Guardrail 4 — No Deprecated Symbol Export

**Rule:** Removed callables must not re-appear in the public surface.

```
# Pseudocode
FORBIDDEN_EXPORTS = [
    "<deprecated_fn_1>",
    "<deprecated_fn_2>",
    "<BINARY_NAME_SLUG>",
]

test "no deprecated symbols exported":
    public_surface = get_exports(<PKG_ROOT>)
    leaked = public_surface ∩ FORBIDDEN_EXPORTS
    assert leaked is empty
```

Language notes:

| Language | Public surface to check |
|----------|------------------------|
| Python | `__all__` + `dir(module)` |
| TypeScript/JS | barrel `index` exports |
| Go | exported (capitalized) identifiers in package root |
| Rust | `pub` items in `lib.rs` / `mod.rs` |

## Running All Guardrails

```bash
# Run as a group for clear CI labeling
<TEST_CMD> tests/architecture/
# or
<TEST_CMD> --filter "architecture|guardrail|root_layout|no_duplicate|import_boundary|no_deprecated"
```

Add guardrail tests as a named CI step (e.g. `architecture-check`) separate from the main test suite so failures are unambiguously labeled.

## Guardrail Lifecycle

| Phase | Action |
|-------|--------|
| Start of migration | Add guardrails with full `COMPAT_ALLOWLIST` |
| Each cleanup PR | Remove entries from `COMPAT_ALLOWLIST` as files are deleted |
| End of migration | `COMPAT_ALLOWLIST` is empty; `ALLOWED_ROOT_FILES` is final |
| Ongoing | Guardrails remain in CI permanently — never remove them |
