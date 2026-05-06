---
name: gsd-workflow-auditor
description: "Audit and realign a Get Shit Done workflow by reviewing project state, planning snapshots, phase status, and prior work. WHEN: \"where are we in GSD\", \"audit our GSD workflow\", \"realign the phase plan\", \"what should we do next\", \"we are off track\"."
---

# GSD Workflow Auditor

Audit the current project state and realign the GSD workflow around the correct next phase.

## Workflow

1. **Establish source of truth**
   - Identify current GSD state files, planning snapshots, phase folders, TODOs, and recent execution notes.
   - Treat current GSD artifacts as primary.
   - Treat older assistant/tool logs as historical context unless the user says otherwise.

2. **Determine current place**
   - Summarize active phase, phase status, blockers, and completed work.
   - Identify whether the team should discuss, plan, revise, execute, or pause a phase.

3. **Detect drift**
   - Compare current GSD phase direction against the user's stated priority.
   - Flag work that is premature, stale, duplicated, or outside the current phase.

4. **Realign workflow**
   - Recommend the next GSD command or phase action.
   - Provide a paste-ready `/gsd-discuss`, `/gsd-plan-phase`, `/gsd-revise-phase`, `/gsd-execute-phase`, or `/gsd-progress` prompt when useful.

5. **Produce checkpoint**
   - Output a concise state summary:
     - Current phase
     - Actual priority
     - Drift or mismatch
     - Recommended next action
     - Acceptance criteria for getting back on track

## Output Format

```markdown
## Current Place

[Brief summary of where the project is now.]

## Drift / Misalignment

[What is off-track, premature, stale, or unclear.]

## Recommended GSD Move

[Next command or workflow step.]

## Paste-Ready Prompt

```text
[Prompt or command to paste into GSD]
```

## Acceptance Criteria

- [ ] [Criterion 1]
- [ ] [Criterion 2]
- [ ] [Criterion 3]
```

## Guardrails

- Do not continue implementation work during the audit.
- Do not promote old backlog notes above current GSD state unless the user explicitly re-prioritizes them.
- Do not assume the active phase is correct; verify it against current artifacts and user intent.
- Prefer realignment over expanding scope.
- Keep the next move small, executable, and phase-compatible.
