# Documentation Index

Use this page to choose the right documentation surface for using, understanding, maintaining, or developing this repository.

## Start here

| Need | Read |
|---|---|
| Set up the project and run first commands | `docs/getting-started.md` |
| Understand architecture, data flow, and integration contracts | `docs/architecture.md` |
| Follow coding, runtime, and compatibility conventions | `docs/standards.md` |
| Find implementation patterns and hotspots | `docs/patterns.md` |
| Release or publish the package | `docs/publishing.md` |
| Review brownfield documentation claims | `docs/audits/brownfield-documentation-review-checklist.md` |
| Maintain local Serena memory state | `.serena/memories/README.md` |

## Enduring docs

| Document | Purpose | Status |
|---|---|---|
| `docs/getting-started.md` | Getting started / setup | Active |
| `docs/architecture.md` | Architecture / design reference | Active |
| `docs/standards.md` | Engineering standards | Active |
| `docs/patterns.md` | Patterns / implementation reference | Active |
| `docs/publishing.md` | Release runbook | Active |
| `docs/security/dependency-security-posture.md` | Security / dependency posture | Active |
| `docs/audits/dependency-audit.md` | Dependency audit | Active |
| `docs/decisions/2026-04-29-rollout-compatibility.md` | Decision / rollout gate | Active |
| `docs/audits/brownfield-documentation-review-checklist.md` | Review checklist | Active |

## Archived process artifacts

These files are preserved outside `docs/` because they are state snapshots, AI work logs, planning reports, or historical process notes rather than enduring project documentation.

| Archived artifact | Former role |
|---|---|
| `.archived/docs/current-state-2026-05-08.md` | Status / source-of-truth snapshot |
| `.archived/docs/state-consolidation-2026-05-08.md` | Memory/workflow consolidation report |
| `.archived/docs/state-consolidation-2026-04-30.md` | Earlier state consolidation report |
| `.archived/oracle-pack-2026-01-04.md` | Archived repository knowledge-pack evidence |
| `.archived/docs/graph-renderer-cytoscape-plan.md` | Historical graph-renderer plan |
| `.archived/docs/hyperbrowser-oss-replacement-plan.md` | Historical replacement plan |
| `.archived/docs/oss-alternatives-hypergraph.md` | Historical alternatives note |


## Local docs site

This repository uses Rspress for the local documentation site.

```bash
pnpm run docs:dev
pnpm run docs:build
pnpm run docs:preview
```

The site root is `docs/`, the generated output is `doc_build/`, and `doc_build/` is ignored because it can be regenerated.

## Organization conventions

- Keep root `README.md` focused on overview, install, quick start, and entry-point links.
- Keep enduring project docs under `docs/`.
- Use subdirectories for durable categories when useful: `docs/security/`, `docs/audits/`, and `docs/decisions/`.
- Keep dated status reports, AI working records, state-consolidation notes, and planning scratchpads outside `docs/`, usually under `.archived/docs/`.
- Do not delete stale docs; move, archive, or mark them historical while preserving provenance.
- Prefer `.serena/memories/README.md` for local agent memory classification instead of duplicating memory details in every doc.
