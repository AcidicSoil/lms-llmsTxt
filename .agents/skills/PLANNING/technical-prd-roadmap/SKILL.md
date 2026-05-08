---
name: technical-prd-roadmap
description: "Generate implementation-ready PRDs and staged roadmap chains using base PRD and RPG dependency templates. WHEN: \"write PRD\", \"create roadmap\", \"approved proceed\", \"implementation PRD\", \"RPG PRD\", \"Task Master PRD\", \"dependency-aware roadmap\"."
license: MIT
metadata:
  author: OpenAI
  version: "2.0.0"
---

# Technical PRD Roadmap

Use this skill to convert scope decisions, planning notes, transcripts, or approved implementation paths into dependency-aware technical PRDs.

## Workflow

1. **Extract scope** — Identify approved direction, target users, success metrics, non-goals, constraints, and evidence gaps.
2. **Choose depth** — Use the [base PRD template](templates/base-prd-template.txt) for concise product plans or the [RPG PRD template](templates/rpg-prd-template.txt) for dependency-aware implementation plans.
3. **Separate WHAT from HOW** — Draft capabilities and features first, then map them to repository modules.
4. **Build dependency order** — Define foundation modules, layered dependencies, and phase entry/exit criteria.
5. **Make it executable** — Add acceptance criteria, test strategy, artifacts, risks, mitigations, and handoff commands.
6. **Split roadmaps** — When scope is broad, produce sequenced PRDs instead of one oversized PRD.

## Reference Guides

- [PRD generation workflow](references/prd-generation-workflow.md)
- [RPG quick guide](references/rpg-method/README.md)
- [Task Master handoff](references/task-master-handoff.md)
- [Quality checklist](references/checklists/prd-quality-checklist.md)
- [Error handling](references/error-handling.md)

## Output Rules

- Do not include timelines unless the user explicitly asks.
- Prefer dependency order over calendar order.
- Keep MVP scope usable and visible as early as possible.
- Do not invent codebase facts; mark assumptions and required inspection.
- For broad initiatives, end each PRD with the next logical PRD.
