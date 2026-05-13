# Technical PRD Roadmap Skill

This bundle contains an Agent Skill for creating implementation-ready PRDs and staged technical roadmap chains.

## Contents

- `SKILL.md` — activation instructions
- `templates/base-prd-template.txt` — concise PRD template supplied by the user
- `templates/rpg-prd-template.txt` — full RPG dependency-aware PRD template supplied by the user
- `templates/strict-dependency-aware-prd-prompt.md` — strict PRD generator prompt supplied by the user
- `templates/combined-prd-output-outline.md` — exact dependency-aware output outline
- `references/` — concise guides for workflow, RPG usage, Task Master handoff, quality checks, prompt examples, and error handling
- `assets/section-map.json` — section mapping metadata
- `scripts/validate-skill.py` — local structural validation helper

## How to Use

Copy this folder into your skills directory as `technical-prd-roadmap/`. Use it when asking for PRDs, roadmap chains, RPG plans, or Task Master-ready implementation documents.

For strict dependency-aware PRDs, use `templates/strict-dependency-aware-prd-prompt.md` and preserve the 11-section order in `templates/combined-prd-output-outline.md`.
