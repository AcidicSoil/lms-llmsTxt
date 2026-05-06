# Runtime Evidence

Use this before editing docs when behavior was learned from CLI execution, browser automation, logs, or generated artifacts.

## Evidence Sources

| Source | Capture |
|---|---|
| CLI help | Command names, flags, defaults, examples |
| Source code | Parser definitions, option defaults, output paths |
| Tests | Expected behavior and regressions |
| Runtime logs | Actual pass/fail state, recovery counts, warnings |
| Artifacts | File names, schemas, summary fields, session pointers |
| Live session | Liveness, confirmation behavior, final UI state |

## Rules

1. Prefer observed behavior over intended behavior.
2. Do not document speculative features as complete.
3. Preserve exact names for commands, flags, files, JSON keys, and directories.
4. Capture both success and recovery behavior when users rely on operations guidance.
5. Note missing evidence in the final report instead of filling gaps from memory.

## Minimum Evidence Bundle

For runtime docs, collect:

- command or entry point invoked
- environment/profile assumptions
- emitted files and their paths
- outcome and error/recovery counts
- post-run state that affects operator usage
