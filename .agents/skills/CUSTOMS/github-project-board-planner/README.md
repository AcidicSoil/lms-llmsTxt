# GitHub Project Board Planner Skill Bundle

This bundle combines the GitHub Project Board Architect workflow into a reusable Agent Skill.

## Contents

- `SKILL.md` — activation metadata and concise workflow instructions.
- `references/` — split rule files loaded on demand.
- `combined-system-prompt.md` — authoritative assembled prompt.
- `single-unit-compact-prompt.md` — compact single-file prompt variant.
- `assets/source/` — original uploaded source files and manifest.

## Primary Use

Use this skill to generate GitHub Projects v2 board plans from `tasks.json`, `PRD.txt`, and/or `README.md`, producing one of:

- Bash script using GitHub CLI
- Portable issue-import CSV
- Structured JSON project payload
