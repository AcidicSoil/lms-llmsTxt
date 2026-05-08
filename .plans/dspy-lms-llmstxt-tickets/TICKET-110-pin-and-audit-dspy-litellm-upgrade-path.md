---
ticket_id: "tkt_lmsllmstxt_pin_audit_deps"
title: "DSPy and LiteLLM upgrade path is pinned and audited before new planner work"
agent: "codex"
done: true
goal: "The codebase has a reviewed, pinned dependency path for recent DSPy capabilities before newer planner or optimizer work is enabled."
---

## Tasks
- Pin DSPy, LiteLLM, and relevant transitive dependencies to reviewed versions before enabling recent DSPy additions.
- Audit dependency and security considerations called out in the handoff, with emphasis on LiteLLM.
- Record upgrade constraints or blockers that affect later evidence-planning, optimizer, or RLM work.

## Acceptance criteria
- A pinned, reviewable dependency set exists for the DSPy and LiteLLM upgrade path.
- Upgrade constraints or blockers are documented for downstream planner, optimizer, and RLM tickets.
- No unpinned or casual upgrade path remains for the new DSPy integration.

## Tests
- Install dependencies from the pinned set or lockfile and verify resolution succeeds.
- Run a smoke test of the current generator against the pinned dependency set and record any blocker explicitly.

## Completion evidence
- `pyproject.toml` pins `dspy-ai==3.1.0` and `litellm==1.80.5`.
- `uv.lock` records the pinned `dspy`, `dspy-ai`, and `litellm` versions and `uv lock --check` resolves successfully.
- `docs/audits/dependency-audit.md` records the DSPy/LiteLLM upgrade constraints and downstream blockers for planner, optimizer, and RLM work.
- `uv run --extra test pytest -q` reported `71 passed, 1 skipped, 6 warnings`; the skip is the LM Studio/GitHub credential integration test when the configured GitHub token is invalid or unauthorized.

## Notes
- Source: "Pin and audit DSPy/LiteLLM dependencies before upgrading", "Recent LiteLLM security notices mean any DSPy upgrade path should be dependency-pinned and audited."
- Constraints:
  - Do not introduce new DSPy-dependent planner behavior until the upgrade path is reviewed.
  - Use verified safe LiteLLM versions rather than unpinned upgrades.
- Evidence:
  - DSPy upgrade discussion
  - LiteLLM security warning in the handoff
- Dependencies: Not provided
- Unknowns:
  - Exact approved versions are not provided.
  - Existing package manager and lockfile format are not provided.
