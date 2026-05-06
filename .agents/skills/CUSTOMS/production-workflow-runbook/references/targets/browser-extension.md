# Browser Extension Runbook

## End State

Secure, reviewable browser extension with reliable content-script behavior, clear permissions, and polished UX.

## Critical Tracks

- permission model
- content-script reliability
- browser compatibility
- settings UX
- packaging/review compliance
- telemetry/debugging

## Workflow

1. Define page surfaces, browser targets, permission needs, local/remote behavior, and data handling.
2. Design popup/options/background/content split, message passing, storage, permission escalation, and CSP constraints.
3. Establish manifest, build system, local loading workflow, release packaging, debug logging, and settings panel.
4. Build slices: install/onboarding, popup/settings, content-script injection, main action flow, auth/storage/sync, diagnostics.
5. Harden: page compatibility, DOM mutation resilience, permission minimization, CSP edge cases, browser-store compliance, upgrade path.
6. Polish: predictable injection, clear permission explanations, polished popup/settings UX, recovery when page context changes.

## Production Checklist

- minimal permissions
- privacy docs complete
- store listing assets ready
- browser review checklist complete
- telemetry or debug export available
- update behavior tested
- support path documented

## Brownfield Notes

Avoid breaking users on pages with changed structure. Version-gate major content-script changes and include kill switches where practical.
