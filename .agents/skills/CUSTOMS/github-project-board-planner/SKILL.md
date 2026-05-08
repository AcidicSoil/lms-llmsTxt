---
name: github-project-board-planner
description: "Create GitHub Projects v2 board plans and import artifacts from task, PRD, or README files. WHEN: \"create GitHub project board\", \"generate issue backlog\", \"turn PRD into GitHub issues\", \"make project import script\", \"GitHub Projects v2 roadmap\"."
license: MIT
metadata:
  author: generated
  version: "1.0.0"
---

# GitHub Project Board Planner

Use this skill to convert `tasks.json`, `PRD.txt`, and/or `README.md` into a GitHub Projects v2 roadmap plus a ready-to-run or ready-to-import artifact.

## Workflow

1. Determine `OUTPUT_MODE`: `script`, `csv`, or `json`; default to `script`.
2. Parse source files in priority order: `tasks.json` > `PRD.txt` > `README.md`.
3. Build a normalized plan with project overview, 3–6 deliverable milestones, at least 10 high-level issues, and backlog items.
4. Apply the issue, milestone, label, dependency, and body rules in [planning rules](references/03-planning-model-and-issue-rules.md).
5. For script output, follow [GitHub Projects v2 script rules](references/04-github-v2-script-rules.md).
6. Emit exactly one artifact using [output modes](references/05-output-modes.md), then validate against [construction and validation](references/06-construction-validation-and-emission.md).

## Constraints

- Use GitHub Projects v2, not classic Projects.
- Do not invent assignees or exact dates.
- Keep issue titles imperative, scoped, concise, and implementation-ready.
- Put dependencies in issue bodies unless a verified native dependency API is used.
- Return only the selected artifact; no explanation or rationale outside it.

## References

- [Role and objective](references/01-role-and-objective.md)
- [Operating mode and inputs](references/02-operating-mode-and-inputs.md)
- [Planning rules](references/03-planning-model-and-issue-rules.md)
- [GitHub Projects v2 script rules](references/04-github-v2-script-rules.md)
- [Output modes](references/05-output-modes.md)
- [Construction and validation](references/06-construction-validation-and-emission.md)
