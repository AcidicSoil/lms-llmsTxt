## Operating Mode

- **OUTPUT_MODE**: one of `script` | `csv` | `json`. Default: `script`.
- **CANVAS_DELIVERY**: If the platform supports a canvas, render the final artifact into a single canvas document named `GitHub_Project_Plan.<ext>`, where `<ext>` is `sh`, `csv`, or `json` based on **OUTPUT_MODE**. Otherwise return inline inside exactly one fenced code block.
- **REVEAL POLICY**: Reason privately. Emit only the selected artifact. Do not include explanations, rationale, or analysis outside the artifact.

---

## Inputs

You may receive any subset of these files:

- `tasks.json`: Canonical task list and subtasks. Treat as authoritative for task inventory, hierarchy, and completion scope.
- `PRD.txt`: Product requirements. Parse into milestones, deliverables, features, risks, dependencies, and acceptance criteria.
- `README.md`: Project context, goals, setup, scope, constraints, terminology, and implementation assumptions.

If multiple files are present, resolve conflicts in this priority order:

1. `tasks.json`
2. `PRD.txt`
3. `README.md`

Deduplicate tasks by semantic equivalence. Preserve meaningful source references.

If inputs are incomplete, still emit a sensible baseline plan from the available project context and common delivery scaffolding. Mark inferred work through `Source: inferred` inside issue bodies or JSON fields.

---
