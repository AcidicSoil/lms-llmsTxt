---
name: parity-check-audit
description: Use when comparing two versions of an application to verify feature parity, catch subtle regressions, and track that intricate details are correctly rebuilt across versions.
argument-hint: <original-path> <new-path> [--focus "area"] [--depth quick|standard|deep]
---

# Parity Check Audit

Compare two versions of an application to find subtle differences — track that features, behaviors, and intricate details are correctly rebuilt and preserved across versions.

## The Discipline

Rebuilds and rewrites silently drop details. A function signature matches but the error handling differs. A UI component renders but the edge-case behavior changed. A config option exists but its default shifted. These subtle losses compound into broken user experiences. This skill enforces systematic comparison so nothing slips through.

## When to Use This Skill

- Verifying a rewrite or rebuild against the original
- Comparing a forked version against upstream
- Auditing a migration (framework, language, architecture)
- Checking that a refactor preserved all original behavior
- Reviewing a vendor replacement or library swap
- Validating that a new version matches the spec of the old

## Phase 1: Establish Sources

Before comparing anything, lock down what you're comparing.

1. **Identify the Original (Source of Truth)**
   - Path, git ref, branch, or tag representing the "correct" version
   - Ask: "What version is the baseline?" if not obvious

2. **Identify the New Version (Under Audit)**
   - Path, git ref, branch, or tag representing the rebuilt/rewritten version

3. **Determine Comparison Mode**
   - **Directory vs Directory**: Two local paths (e.g., `./app-v1/` vs `./app-v2/`)
   - **Git Ref vs Git Ref**: Two branches, tags, or commits in the same repo
   - **Remote vs Local**: Clone/fetch the original if needed

4. **Scope the Audit**
   - Full application or specific subsystems?
   - Are there known intentional changes to exclude?
   - What's the user's primary concern? (functionality? performance? security?)

Document the sources clearly before proceeding:

```
Original: [path/ref]
New:      [path/ref]
Mode:     [directory|git-ref|remote]
Scope:    [full|subsystem list]
Exclusions: [intentional changes to skip]
```

## Phase 2: Structural Mapping

Map the architecture of both versions side by side.

### 2a: File Inventory

Use `Glob` and directory listing to build a file manifest for both versions:

- Files present in original but **missing** from new version
- Files present in new version but **not in** original (additions)
- Files present in **both** (candidates for detailed comparison)
- Files that were **renamed or moved** (detect by content similarity)

Output a structural diff table:

```
| Status    | Original Path              | New Path                   | Notes          |
|-----------|----------------------------|----------------------------|----------------|
| MISSING   | src/auth/oauth.ts          | —                          | OAuth removed? |
| ADDED     | —                          | src/auth/sso.ts            | New SSO impl   |
| RENAMED   | lib/utils/format.ts        | src/helpers/formatting.ts  | Path changed   |
| MATCHED   | src/api/routes.ts          | src/api/routes.ts          | Compare next   |
```

### 2b: Dependency Comparison

Compare dependency manifests (`package.json`, `requirements.txt`, `go.mod`, `Cargo.toml`, etc.):

- Libraries removed (potential feature loss)
- Libraries added (new capabilities or replacements)
- Version changes (potential behavior differences)
- Dev vs production dependency shifts

### 2c: Configuration Comparison

Compare all config files (`.env.example`, config files, CI/CD, build configs):

- Missing config keys
- Changed defaults
- New required configuration
- Environment variable differences

## Phase 3: Feature Extraction

This is the core of the audit. Extract a feature inventory from the original, then verify each feature exists in the new version.

### 3a: Extract Features from Original

Read through the original codebase systematically. For each module/file, extract:

- **Exported functions/methods** — name, parameters, return type, purpose
- **API endpoints** — method, path, request/response shape, auth requirements
- **UI components** — what they render, props they accept, states they handle
- **Event handlers** — what triggers them, what they do
- **Error handling** — what errors are caught, how they're handled, what messages surface
- **Edge cases** — null checks, boundary conditions, fallback behavior
- **Configuration options** — what's configurable, defaults, validation rules
- **Side effects** — database writes, API calls, file I/O, logging, analytics

Build a **Feature Registry** — a checklist of every discrete behavior:

```
## Feature Registry

### Module: Authentication
- [ ] FR-001: Login with email/password — validates format, rate-limits attempts, returns JWT
- [ ] FR-002: Password reset flow — sends email, expires token after 24h, enforces complexity
- [ ] FR-003: Session timeout — 30min idle, warns at 25min, preserves unsaved form data
- [ ] FR-004: OAuth Google login — redirects, handles callback, creates account if new

### Module: API
- [ ] FR-005: GET /users/:id — returns 404 if not found, strips sensitive fields for non-admin
- [ ] FR-006: Rate limiting — 100 req/min per IP, returns 429 with Retry-After header
```

### 3b: Verify Each Feature in New Version

For every feature in the registry, search the new codebase:

1. **Find the corresponding code** — use `Grep` for function names, route paths, component names
2. **Read the implementation** — don't just confirm existence, read the actual logic
3. **Compare behavior** — does it handle the same inputs, edge cases, error conditions?
4. **Grade the match**:

| Grade | Meaning | Action Required |
|-------|---------|-----------------|
| EXACT | Identical behavior, same or equivalent implementation | None |
| EQUIVALENT | Different implementation, same observable behavior | Document the difference |
| PARTIAL | Some behavior preserved, some missing or changed | Flag for review |
| MISSING | Feature not found in new version | Critical finding |
| DIVERGED | Feature exists but behaves differently | Document old vs new behavior |
| IMPROVED | Feature exists with additional/better behavior | Note as intentional if confirmed |

Update the Feature Registry with grades:

```
- [x] FR-001: Login with email/password — EXACT
- [~] FR-002: Password reset flow — PARTIAL: token expiry changed from 24h to 1h
- [ ] FR-003: Session timeout — MISSING: no idle detection found
- [x] FR-004: OAuth Google login — EQUIVALENT: uses different library, same flow
```

## Phase 4: Deep Comparison

For all MATCHED files and any PARTIAL/DIVERGED features, perform line-level analysis.

### 4a: Logic Comparison

For each paired file, compare:

- **Control flow** — are the same branches/conditions present?
- **Error paths** — does the new version handle the same failure modes?
- **Data transformations** — same input produce same output?
- **Ordering and sequencing** — operations happen in the same order where it matters?
- **Defaults and fallbacks** — same default values, same fallback behavior?

### 4b: Subtle Difference Patterns

Watch specifically for these common silent regressions:

| Pattern | Example | Why It Matters |
|---------|---------|----------------|
| **Swallowed errors** | `catch(e) {}` replacing `catch(e) { log(e); notify() }` | Failures become invisible |
| **Loosened validation** | Removed input sanitization or length checks | Security regression |
| **Changed defaults** | Timeout changed from 30s to 5s, or vice versa | Different behavior under load |
| **Missing null checks** | Original checked `if (user?.email)`, new uses `user.email` | Crash on edge case |
| **Dropped event emissions** | Original emitted events for analytics/logging, new doesn't | Lost observability |
| **Hardcoded values** | Original read from config, new hardcodes the value | Lost configurability |
| **Race conditions** | Original used mutex/lock, new doesn't synchronize | Intermittent bugs |
| **Type narrowing** | Original distinguished string|number, new treats as any | Runtime type errors |
| **Missing cleanup** | Original had teardown/dispose, new leaks resources | Memory/connection leaks |
| **Altered return shapes** | Same function name but different return structure | Breaks callers |

### 4c: Test Comparison

Compare test suites between versions:

- Tests in original with no equivalent in new version (lost coverage)
- Test assertions that changed (behavior expectation shifts)
- Edge case tests that were dropped
- New tests that don't exist in original (verify they're valid)

## Phase 5: Produce Audit Report

Generate the final report at `.parity-audit/[name]-[YYYY-MM-DD].md`:

```markdown
# Parity Check Audit: [Application Name]

**Date**: YYYY-MM-DD
**Original**: [path/ref]
**New Version**: [path/ref]
**Scope**: [full|subsystem]
**Auditor**: Claude Code (parity-check-audit skill)

## Executive Summary

[2-3 sentences: overall parity status, critical gaps count, confidence level]

**Parity Score**: X/Y features verified (Z%)

## Structural Differences

[Table from Phase 2: missing files, additions, renames]

## Dependency Changes

[From Phase 2b: removed/added/changed libraries]

## Configuration Differences

[From Phase 2c: missing keys, changed defaults]

## Feature Parity Registry

[Full registry from Phase 3 with grades]

### Critical: Missing Features
[Features graded MISSING — these are the highest priority]

### Warning: Partial Implementations
[Features graded PARTIAL — behavior gaps documented]

### Info: Diverged Behavior
[Features graded DIVERGED — different but functional]

### Verified: Exact/Equivalent
[Features confirmed as matching]

## Subtle Differences Found

[From Phase 4: specific line-level findings with file:line references]

### Silent Regressions
[Swallowed errors, loosened validation, changed defaults, etc.]

### Behavioral Shifts
[Same feature, different behavior — with before/after comparison]

## Test Coverage Comparison

[From Phase 4c: lost tests, changed assertions, coverage gaps]

## Recommendations

1. **Must Fix**: [Critical gaps that break functionality]
2. **Should Fix**: [Partial implementations that lose important behavior]
3. **Consider**: [Divergences that may be intentional but should be confirmed]
4. **Accepted**: [Known intentional changes, documented and approved]

## Verification Checklist

- [ ] All MISSING features reviewed with stakeholder — confirmed removed or needs implementation
- [ ] All PARTIAL features have tickets/tasks to complete
- [ ] All DIVERGED features confirmed as intentional
- [ ] Test coverage for critical paths verified
- [ ] Configuration parity confirmed for all environments
```

## Depth Options

**Quick**: Phases 1-2 only. Structural mapping + dependency/config diff. Good for initial triage.

**Standard** (default): All 5 phases. Full feature registry and audit report.

**Deep**: All 5 phases + recursive sub-feature extraction (every conditional branch, every error handler, every default value cataloged individually). Use for critical systems or security-sensitive migrations.

## Red Flags: Restart Investigation

If you catch yourself doing any of these, stop and go back:

- Assuming two functions are equivalent because they have the same name
- Skipping error handling comparison because "it probably works"
- Marking something EXACT without reading both implementations
- Ignoring test differences because "tests aren't features"
- Treating a missing feature as intentional without user confirmation

## After the Audit

1. Review findings with the user — confirm which MISSING/PARTIAL items are intentional vs gaps
2. Create tasks for each Must Fix and Should Fix item
3. Re-run specific phases after fixes are applied to verify resolution
4. Keep the audit report as a living document until parity is achieved
