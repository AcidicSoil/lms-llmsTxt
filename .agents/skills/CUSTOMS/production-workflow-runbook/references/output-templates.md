# Output Templates

Use these structures when generating runbooks.

## Standard Runbook

```markdown
# [Target] Production Workflow Runbook

## Assumptions and Scope
- Project state: [brownfield|greenfield]
- Target: [web app|CLI|AI app|...]
- Finish line: production-ready, polished, supportable

## Lifecycle
[Core phases with target-specific details]

## Artifacts
| Artifact | Purpose | Owner |
|---|---|---|

## Target Workflow
[Tracks, slices, hardening, polish]

## Release Gates
[Product, engineering, security, operations, business]

## Verification
[Tests, smoke checks, dashboards, manual checks]

## Launch Plan
[Staging, rollout, rollback, post-launch monitoring]
```

## Target Overlay Block

```markdown
## [Target] Overlay

### End State
[Clear production-ready outcome]

### Critical Tracks
- [track]

### Slice Order
1. [slice]

### Hardening
- [risk check]

### Polish Finish Line
- [UX/devex quality bar]

### Brownfield Notes
- [compatibility/migration concerns]
```

## Minimal Artifact Tree

```text
/planning
  PROJECT.md
  REQUIREMENTS.md
  NON_GOALS.md
  RISKS.md
  ROADMAP.md
  ARCHITECTURE.md
  UX.md
  RELEASE_PLAN.md
  OPERATIONS.md
  TEST_STRATEGY.md
  SECURITY.md
  ANALYTICS.md
  CHANGELOG.md
```

For brownfield add:

```text
/planning/brownfield
  SYSTEM_MAP.md
  DEPENDENCY_AUDIT.md
  BEHAVIOR_BASELINE.md
  MIGRATION_PLAN.md
  COMPATIBILITY_MATRIX.md
```
