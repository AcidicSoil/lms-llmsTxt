---
name: evidence-first-operating-model
description: "Guide assistants through evidence-first autonomous work with local instructions, reversible changes, artifact classification, correction handling, validation, uncertainty reporting, and handoff. WHEN: \"audit and clean up\", \"consolidate docs\", \"regenerate plan\", \"use local instructions\", \"autonomously execute\", \"handoff summary\"."
license: MIT
metadata:
  version: "1.0.0"
---

# Evidence-First Operating Model

Use this skill when a user wants a bounded end-to-end pass over existing context, artifacts, plans, docs, memories, or workflow state.

## Workflow

1. **Inspect first** - Read available context, local instructions, recent artifacts, and relevant state before planning or editing.
2. **Select instructions** - Apply only local instructions that directly match the task; report which ones were used and why.
3. **Classify artifacts** - Separate enduring docs, process notes, working plans, state records, generated outputs, duplicates, stale items, and unknowns.
4. **Plan from evidence** - Build a referenced task list with objective, source, action, risk, and validation for each task.
5. **Execute safely** - Act autonomously when context is sufficient. Prefer reversible edits: merge, rename, archive, mark stale, index, or summarize. Avoid irreversible deletion without explicit approval.
6. **Handle correction** - When the user redirects the goal, preserve useful work, revise the governing model, update affected artifacts, and validate the new direction.
7. **Validate** - Run the smallest non-destructive checks available. If automated checks are absent, provide manual checks and state the gap.
8. **Handoff cleanly** - Return changed/proposed files, validation, assumptions, risks, unknowns, and the next safe action.

## Preserve

- Evidence before assertions.
- Local instructions before generic behavior.
- Autonomous execution when safe.
- Reversible changes over destructive cleanup.
- Explicit classification of artifacts and state.
- Concise uncertainty reporting.
- Correction-responsive replanning.
- Handoff that a future assistant can resume from.

## Avoid

- Asking for clarification when repository/context evidence is sufficient.
- Treating transient process artifacts as enduring documentation.
- Deleting, overwriting, or canonicalizing contested artifacts without approval.
- Hiding uncertainty or inventing missing state.
- Reporting changes without validation.

For the detailed operating model, use [the workflow reference](references/operating-model.md). For response structure, use [the handoff template](templates/handoff-template.md).
