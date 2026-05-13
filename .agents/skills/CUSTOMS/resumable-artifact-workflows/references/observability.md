# Observability

Make normal output concise and raw evidence durable.

## Terminal Output

Default terminal output should show progress, not raw command streams:

```text
[108/155] Human Item Name
  - Opening item
  ✓ Item opened
  - Opening required stage
  ! Stage not visible on attempt 1/4; retrying
  ✓ Output captured
  artifact: runs/.../artifacts/item/output.md
  logs: runs/.../artifacts/item/logs/
```

Use modes such as `--quiet`, `--verbose`, and `--debug` when appropriate. Debug mode may echo full commands and raw stderr.

## Logs

Store per-item raw evidence:

```text
artifacts/<slug>/logs/commands.log
artifacts/<slug>/logs/stdout.log
artifacts/<slug>/logs/stderr.log
```

Filter repeated known-noise from terminal output, but keep it in raw logs.

## Retry and Pacing

For fragile UI, API, or network stages:

1. wait after navigation/open
2. perform action
3. wait for state transition
4. snapshot or probe the stage
5. retry if the expected next stage is absent

Prefer configurable pacing variables. Doubling wait defaults is reasonable when the target system rate-limits fast polling.

## Failure Snapshots

On terminal failure, capture final observable state before exiting:

```text
snapshots/99_failed_before_stage_terminal_snapshot.txt
snapshots/99_failed_no_output_found_terminal_snapshot.txt
snapshots/99_failed_blocked_terminal_snapshot.txt
```

Write the snapshot path into the status marker. These snapshots support future patches for blockers, popups, auth walls, or changed selectors.
