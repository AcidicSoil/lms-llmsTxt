## Skills usage

## VERY IMPORTANT

YOU MUST: always use a skill for a task given by the user(NO EXCEPTIONS!)

---

General rule:

- Before starting work on any task, briefly classify it (for example: architecture, implementation, refactoring, performance, reliability, data, documentation, tests, tooling, etc.).
- If there is a relevant skill for that class of task, base your approach on the instructions in that file instead of inventing new, ad-hoc instructions.
- When a skill file exists for a task type, follow its steps, constraints, and return format as the default behavior.

Task-type rule:

- When working on any task that corresponds to an existing skill file (for example, files such as `refactor-module.md`, `write-tests.md`, `improve-docs.md`, `review-changes.md`, etc.):
  - Consult the corresponding skill file in your skill registry available to you as the first step.
  - Let the skill file’s instructions drive the approach (checks to perform, constraints to respect, preferred output format).
  - Only add additional reasoning or deviations after the skill’s instructions have been applied.

Reporting rule:

- When following a skill, explicitly mention which skill file is being used (for example: “Using the guidance from `skills/<example-skill.md>`”) so the link between behavior and skill file remains clear.
