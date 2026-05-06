---
name: tui-design-orchestration
description: Orchestrate Ratatui design critique, component planning, parallel implementation, and final polish with @tui_designer.
---

## What I do

- Route Ratatui design work through `@tui_designer` with a repeatable critique-to-build loop.
- Require `@explore` context gathering before major design decisions.
- Encourage parallel component implementation, then parent-agent integration and final design QA.
- Enforce a parent-orchestrated loop where the first design pass returns critique notes and a desired TODO backlog.

## When to use me

Use this skill when the user asks for TUI redesign, visual polish, UX critique, componentization, or Ratatui layout/widget improvements.

## Required workflow

1. Invoke one broad `@tui_designer` first pass to produce:
   - prioritized critique notes
   - desired TODO backlog broken into small tasks
2. Parent agent converts that backlog into scoped work items and ownership.
3. Parent agent runs `@explore` context gathering for target files before implementation handoffs.
4. Spawn multiple focused `@tui_designer` tasks in parallel when independent (one component or concern per task).
5. Parent agent integrates all subtask outputs, resolves overlap, and validates behavior.
6. Run one final `@tui_designer` review pass for consistency feedback and finishing advice.

## Handoff template

Use this structure when delegating to `@tui_designer`:

- Goal: <design objective>
- Scope: <file paths or screen areas>
- Context: <findings from `@explore` and ratatui docs snapshots>
- Constraints: <behavioral, style, keyboard UX, performance>
- Deliverable: <critique, component plan, implementation, or final review>

## Return checklist

- First-pass critique findings and priority order
- Desired TODO backlog (small, dispatchable tasks)
- Scoped subtask/ownership split prepared for parent orchestration
- Integration notes for parent assembly
- Final polish feedback from closing design pass
