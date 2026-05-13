---
name: technical-prd-roadmap
description: "Generate dependency-aware PRDs and staged implementation roadmaps. WHEN: "write PRD", "create roadmap", "implementation PRD", "RPG PRD", "Task Master PRD", "dependency-aware PRD", "approved proceed"."
license: MIT
metadata:
  author: OpenAI
  version: "2.1.0"
---

# Technical PRD Roadmap

Use this skill to convert scope decisions, planning notes, transcripts, or approved implementation paths into implementation-ready PRDs.

## Workflow

1. **Extract scope** — Identify problem, users, success metrics, constraints, integrations, assumptions, non-goals, and evidence gaps.
2. **Choose template** — Use the [base PRD template](templates/base-prd-template.txt), [RPG PRD template](templates/rpg-prd-template.txt), or [strict dependency-aware PRD prompt](templates/strict-dependency-aware-prd-prompt.md).
3. **Separate WHAT from HOW** — Draft capability domains and atomic features first, then map them to modules, files, functions, or classes.
4. **Order by dependency** — Build an acyclic dependency chain from foundation modules to higher layers, then derive phases from that topology.
5. **Make tasks executable** — Each phase task needs dependencies, acceptance criteria, and test strategy. Avoid timelines unless explicitly requested.
6. **Close with handoff structure** — End dependency-aware PRDs with recommended counts for epics, implementation tasks, and subtasks.

## Reference Guides

- [PRD generation workflow](references/prd-generation-workflow.md)
- [RPG quick guide](references/rpg-method/README.md)
- [Task Master handoff](references/task-master-handoff.md)
- [Quality checklist](references/checklists/prd-quality-checklist.md)
- [Error handling](references/error-handling.md)
- [Prompt examples](references/prompt-examples.md)

## Output Rules

- Use exact 11-section order for strict dependency-aware PRDs; see [combined output outline](templates/combined-prd-output-outline.md).
- Every feature must list Description, Inputs, Outputs, Behavior, and MVP status.
- Every module must have one responsibility and explicit public exports.
- Dependency graphs must be acyclic and include a nonempty foundation layer.
- Phases must derive from dependencies, not calendar timelines.
- State assumptions when repository facts or prior research are missing.
