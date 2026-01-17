## Skills usage

You have a library of reusable skill prompts stored under `$CODEX_HOME/skills/` (commonly `~/.codex/skills/`).

Treat each **skill folder** in `$CODEX_HOME/skills/` as a named skill:

- A folder `$CODEX_HOME/skills/<SKILL_NAME>/SKILL.md` defines the canonical flow and constraints for the `<SKILL_NAME>` skill.
- Skill folders may also include `scripts/`, `references/`,`templates`, and `assets/` that the assistant should use when the skill requires them.
- These skills are the primary reference for how to handle common or important task types.

General rule:

- Before starting work on any task, briefly classify it (for example: architecture, implementation, refactoring, performance, reliability, data, documentation, tests, tooling, pack generation, etc.).
- If there is a relevant skill under `$CODEX_HOME/skills/` for that class of task, base the approach on the instructions in that skill instead of inventing new, ad-hoc instructions.
- When a skill exists for a task type, follow its steps, constraints, and return format as the default behavior.
- If you cannot find a skill ensure you mention there is not a suitable skill for this interaction and prompt user to create,retrieve, and/or ask you to create one.

Task-type rule:

- When working on any task that corresponds to an existing skill:
  - Consult the corresponding `$CODEX_HOME/skills/<SKILL_NAME>/SKILL.md` as the first step.
  - Let the skill’s instructions drive the approach (checks to perform, constraints to respect, preferred output format).
  - Only add additional reasoning or deviations after the skill’s instructions have been applied.

Reporting rule:

- When following a skill, explicitly mention which skill is being used (for example: “Using the guidance from `$CODEX_HOME/skills/<SKILL_NAME>/SKILL.md`”) so the link between behavior and skill remains clear.
- Do not modify or overwrite skill files themselves unless explicitly instructed to adjust the underlying skill behavior.
