# Watchdog Signals

Use observable UI state to decide whether the loop is progressing, complete, or stuck.

## State Classification

| State | Signals | Action |
|---|---|---|
| `ready` | Composer available, no active streaming | Submit next allowed prompt. |
| `confirming` | Confirmation card and buttons visible | Apply confirmation policy. |
| `streaming` | Assistant text or tool status changing | Continue polling. |
| `completed` | Stable assistant answer with no blocking card | Record outcome. |
| `idle-stall` | Repeated tool-status text without answer progress | Refresh and reattach if within limit. |
| `login-lost` | Sign-in page, auth wall, empty profile | Stop and report. |
| `stale-tab` | Dead target, missing ChatGPT shell, detached tab | Reattach once; then stop. |

## Guardrails

Do not treat a bare tool-status line as completion. Require an answer-like terminal state or an explicit error. Make thresholds explicit in config or artifacts; avoid hidden retry heuristics.
