## Skills usage

You have a library of reusable skill prompts stored under `$CODEX_HOME/skills/`.

Treat each file in `~/.codex/skills/` as a named skill:

- A file `~/.codex/skills/<DOMAIN>/<NAME>.md` defines the canonical flow and constraints for the `<NAME>` skill.
- These skills are the primary reference for how to handle common or important task types.

General rule:

- Before starting work on any task, briefly classify it (for example: architecture, implementation, refactoring, performance, reliability, data, documentation, tests, tooling, etc.).
- If there is a relevant skill file in `~/.codex/skills/` for that class of task, base your approach on the instructions in that file instead of inventing new, ad-hoc instructions.
- When a skill file exists for a task type, follow its steps, constraints, and return format as the default behavior.

Task-type rule:

- When working on any task that corresponds to an existing skill file (for example, files such as `refactor-module.md`, `write-tests.md`, `improve-docs.md`, `review-changes.md`, etc.):
  - Consult the corresponding skill file in `~/.codex/skills/` as the first step.
  - Let the skill file’s instructions drive the approach (checks to perform, constraints to respect, preferred output format).
  - Only add additional reasoning or deviations after the skill’s instructions have been applied.

Reporting rule:

- When following a skill, explicitly mention which skill file is being used (for example: “Using the guidance from `prompts/skills/refactor-module.md`”) so the link between behavior and skill file remains clear.
- Do not modify or overwrite the skill files themselves unless explicitly instructed to adjust the underlying skill behavior.
