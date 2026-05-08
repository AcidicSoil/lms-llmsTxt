# GitHub Project Board Architect Bundle Overview

This bundle decomposes the GitHub Project Board Architect system prompt into reusable reference files plus one authoritative assembled output.

## File roles

- `manifest.json` — machine-readable bundle index, assembly order, and authoritative output path.
- `00_overview.md` — human-readable navigation and bundle purpose.
- `01_role_and_objective.md` — role, task, and GitHub Projects v2 constraint.
- `02_operating_mode_and_inputs.md` — runtime modes, canvas delivery, reveal policy, and accepted source documents.
- `03_planning_model_and_issue_rules.md` — issue inventory requirements, internal model, labels, milestones, and issue body contract.
- `04_github_v2_script_rules.md` — GitHub CLI, Projects v2, field, item, label, milestone, issue, and idempotency rules for script mode.
- `05_output_modes.md` — script, CSV, and JSON output specifications.
- `06_construction_validation_and_emission.md` — construction rules, validation checklist, and final emission policy.
- `final_system_prompt.md` — authoritative merged prompt preserved from the provided source.

## Assembly order

1. `01_role_and_objective.md`
2. `02_operating_mode_and_inputs.md`
3. `03_planning_model_and_issue_rules.md`
4. `04_github_v2_script_rules.md`
5. `05_output_modes.md`
6. `06_construction_validation_and_emission.md`

`final_system_prompt.md` is the authoritative production prompt.
