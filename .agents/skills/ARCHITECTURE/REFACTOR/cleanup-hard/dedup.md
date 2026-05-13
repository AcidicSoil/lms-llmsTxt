# Deduplication and Reference Rewrite

Rewrite all references before deleting anything. Full test suite must pass after rewrites and before deletes.

## Rewrite Map Template

From the classification table, produce an explicit old → canonical map:

| Old reference | Canonical reference |
|---------------|---------------------|
| `<OLD_PATH_1>` | `<CANONICAL_PATH_1>` |
| `<OLD_PATH_2>` | `<CANONICAL_PATH_2>` |
| `<PKG_ROOT><SEP>old_module` | `<PKG_ROOT><SEP>domain<SEP>new_module` |

## Procedure

### 1. Find all affected files

```bash
# Find every file importing or referencing old paths
<SCAN_CMD> -rn "<OLD_PATH_1>\|<OLD_PATH_2>\|<OLD_PATH_3>" <PKG_ROOT> tests docs

# Language-specific variants:
# Python:  rg -n "from old_pkg|import old_pkg"
# JS/TS:   rg -n "from ['\"]old-module|require\(['\"]old-module"
# Go:      rg -n "\"github.com/org/repo/old/pkg\""
# Rust:    rg -n "use old_crate::old_module"
```

### 2. Rewrite references

Replace every occurrence of `<OLD_PATH>` with `<CANONICAL_PATH>`.

```
# Pattern (language-neutral)
before: import/from/use/require  <OLD_PATH>
after:  import/from/use/require  <CANONICAL_PATH>
```

Language-specific examples:

```python
# Python — before
from pkg.config import load
from pkg.old_module.agent import build

# Python — after
from pkg.core.config import load
from pkg.integrations.new_module.agent import build
```

```typescript
// TypeScript — before
import { load } from '../shims/config'
import { build } from '../old-module/agent'

// TypeScript — after
import { load } from '../core/config'
import { build } from '../integrations/new-module/agent'
```

```go
// Go — before
import "github.com/org/repo/old/pkg"

// Go — after
import "github.com/org/repo/domain/pkg"
```

### 3. Verify rewrites before deleting

```bash
# Zero hits = safe to delete
<SCAN_CMD> -rn "<OLD_PATH>" <PKG_ROOT> tests
<TEST_CMD>
```

### 4. Delete stale copy

Only after step 3 passes:

```bash
rm -rf <PKG_ROOT>/old_module/
rm <PKG_ROOT>/shim_file.<ext>
```

## Identity Test Pattern

Add before deleting to confirm canonical resolution. Adapt to language test runner:

```
# Pseudocode
for each submodule in [module_a, module_b, module_c]:
    old_ref = load("<OLD_PATH>.<submodule>")
    canonical_ref = load("<CANONICAL_PATH>.<submodule>")
    assert old_ref is canonical_ref   # same object / same resolved module
```

After deletion, update assertions to verify canonical path alone resolves correctly.

## Runtime Asset Verification

If the canonical module contains runtime assets (prompts, templates, data files):

```bash
# Confirm assets exist at canonical location
find <PKG_ROOT>/domain/new_module/assets -type f | sort

# Confirm packaging config includes them
<SCAN_CMD> -n "assets\|include\|package_data" <PACKAGING_CONFIG>
```
