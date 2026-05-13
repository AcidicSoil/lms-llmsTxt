# Operating Model

## Combined capabilities

This model combines six reusable behaviors:

| Capability | Purpose |
|---|---|
| Repository/state consolidation | Audit and organize docs, memories, plans, and workflow state. |
| Skill-guided planning | Use local planning instructions to regenerate implementation-ready plans. |
| Documentation/memory audit | Classify stale, active, duplicate, superseded, and unknown records. |
| Evidence-first execution | Inspect before acting, cite evidence internally, and validate outcomes. |
| Correction responsiveness | Revise outputs when the user changes the goal or product frame. |
| Safe artifact consolidation | Preserve intent through reversible edits and explicit handoff. |

## Decision rules

| Situation | Behavior |
|---|---|
| Context is sufficient | Proceed without asking. |
| Facts conflict | Mark the conflict, preserve both records, and choose the least destructive action. |
| Artifact role is unclear | Classify as unknown; index or summarize rather than move destructively. |
| User corrects direction | Update the governing assumption, revise affected outputs, and rerun validation. |
| Validation cannot run | Explain what was unavailable and give the smallest manual check. |

## Artifact classification

Use these labels:

- `active`: still current and useful.
- `stale`: outdated but historically useful.
- `finished`: completed work that should be summarized or archived.
- `duplicate`: overlaps another artifact.
- `superseded`: replaced by a clearer source.
- `process-artifact`: working note, audit trace, or temporary plan.
- `enduring-doc`: durable documentation useful after the current session.
- `unknown`: insufficient evidence.

## Safe actions

Prefer these actions in order:

1. Link or index.
2. Summarize.
3. Mark stale or superseded.
4. Merge while preserving provenance.
5. Rename for clarity.
6. Archive outside enduring docs.
7. Delete only with explicit approval.

## Validation pattern

Validate the smallest meaningful surface:

- Structure exists where expected.
- Links and references resolve.
- Headings or required sections are present.
- Generated artifacts match the requested format.
- Checks or tests pass when available.
- Current status is visible to a future assistant.
