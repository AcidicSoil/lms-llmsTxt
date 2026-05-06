# Dev Tool Runbook

## End State

Developer tool that reduces engineering friction, is safe to adopt, easy to debug, and does not create operational drag.

## Critical Tracks

- workflow fit
- install/bootstrapping
- compatibility with existing repos/tooling
- diagnostics
- safe automation
- docs and migration

## Workflow

1. Define pain point, current cost/error rate, target users, environments, and integrations.
2. Map current developer flow and insertion point: interactive, background, CI advisory, or CI enforcement.
3. Establish packaging, repo detection, config format, compatibility matrix, dry-run mode, debug mode, rollback/undo where feasible.
4. Build slices: bootstrap/install, project detection/config loading, main automation, reporting, CI integration, editor integration if needed.
5. Harden: monorepos, partial config, permission failures, dirty repo state, file locks, concurrent runs, shell/platform matrix, integration conflicts.
6. Polish: zero-surprise behavior, excellent diagnostics, minimal config burden, safe defaults, docs explaining why and how.

## Production Checklist

- migration guide exists
- compatibility matrix exists
- dry-run available
- debug logging available
- failure recovery documented
- version pinning and update policy defined
- sample repos or fixtures tested

## Brownfield Notes

Do not silently rewrite existing configs. Introduce advisory mode before enforcement. Support incremental adoption and clear opt-out controls.
