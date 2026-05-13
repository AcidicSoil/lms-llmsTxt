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
| Verify MCP server tools in Inspector | `docs/mcp-inspector-payloads.md` |
| Review brownfield documentation claims | `docs/audits/brownfield-documentation-review-checklist.md` |

## Enduring docs

| Document | Purpose | Status |
|---|---|---|
| `docs/getting-started.md` | Getting started / setup | Active |
| `docs/architecture.md` | Architecture / design reference | Active |
| `docs/standards.md` | Engineering standards | Active |
| `docs/patterns.md` | Patterns / implementation reference | Active |
| `docs/publishing.md` | Release runbook | Active |
| `docs/mcp-inspector-payloads.md` | MCP Inspector verification payloads | Active |
| `docs/security/dependency-security-posture.md` | Security / dependency posture | Active |
| `docs/audits/dependency-audit.md` | Dependency audit | Active |
| `docs/decisions/2026-04-29-rollout-compatibility.md` | Decision / rollout gate | Active |
| `docs/audits/brownfield-documentation-review-checklist.md` | Review checklist | Active |

## Internal process artifacts

State snapshots, AI work logs, planning reports, and historical process notes are not part of the public documentation set. Keep them outside `docs/` in an internal working or archive area, and promote only durable maintainer guidance back into `docs/`.

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
- Keep dated status reports, AI working records, state-consolidation notes, and planning scratchpads outside `docs/`, usually under an internal working or archive area.
- Do not delete stale docs; move, archive, or mark them historical while preserving provenance.
- Keep local agent memory and tooling state out of `docs/` unless it becomes a durable maintainer contract.
