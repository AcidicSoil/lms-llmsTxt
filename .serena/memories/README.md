# Serena Memory Index

This directory stores project-local Serena memories for repository agents. Use this index before opening individual dated handoffs.

## Current source of truth

1. `.archived/docs/current-state-2026-05-08.md` — durable repository-state summary.
2. `.archived/docs/state-consolidation-2026-05-08.md` — latest memory/workflow consolidation report.
3. `.serena/memories/current_state_2026_05_08.md` — concise current memory redirect for future agents.
4. `.plans/dspy-lms-llmstxt-tickets/AUDIT-2026-04-29-ticket-state.md` — canonical DSPy ticket-state ledger.
5. `docs/decisions/2026-04-29-rollout-compatibility.md` — rollout gate and compatibility decision.

## Memory classification

| Memory file | Classification | Use |
|---|---|---|
| `current_state_2026_05_08.md` | Active | Start here for concise current state and handoff pointers. |
| `current_state_2026_04_30.md` | Superseded redirect | Preserved for path stability; defer to `current_state_2026_05_08.md` and `.archived/docs/current-state-2026-05-08.md` when status differs. |
| `project_overview.md` | Active | Durable project purpose, runtime layout, and high-level architecture. |
| `style_and_conventions.md` | Active | Durable coding, testing, and compatibility conventions. |
| `suggested_commands.md` | Active | Common setup, test, build, CLI, MCP, and UI commands. |
| `task_completion_checklist.md` | Active | Verification and completion guardrails. |
| `session_handoff_2026_04_29.md` | Superseded evidence | Historical intermediate handoff; do not use as latest task state. |
| `session_handoff_2026_04_29_ticket_170.md` | Finished / superseded evidence | Historical TICKET-170 handoff. |
| `session_handoff_2026_04_29_ticket_190.md` | Finished / superseded evidence | Historical TICKET-190 handoff. |
| `session_handoff_2026_04_29_ticket_210.md` | Finished / superseded evidence | Historical TICKET-210 handoff. |

## Guardrails

- Do not delete stale or superseded memories without explicit approval.
- Prefer redirecting or marking superseded memories over moving/removing them.
- Keep long evidence in docs and plans; keep memories concise and durable.
- Treat rollout owner, rollout approval venue, external benchmark repo set, and model-backed RLM integration surface as `Unknown` until repository evidence resolves them.
- Treat staged `.serena/indexed-search.sh` as active workflow evidence with `Unknown` adoption/approval status until repository evidence resolves it.
- Treat the historical `.ecc-hooks-disable` / `.ecc-hooks-disable.bak` transition intent as `Unknown`; final 2026-05-08 validation found no dirty `.ecc` path diff.
