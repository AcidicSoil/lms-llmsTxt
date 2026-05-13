# Testing and Docs

## Tests to Add

Add focused tests around workflow guarantees, not implementation trivia.

| Case | Expected result |
|---|---|
| delayed next-stage visibility | retries until stage appears, then continues |
| stage never visible | writes failed status and stops or skips according to policy |
| output captured | writes `captured` and checkpoint completed row |
| output verified empty | writes `captured_empty` and skips in future deltas |
| failure after partial artifact | does not count as handled |
| resume after failure | skips completed keys and starts at first unfinished item |
| backfill old artifacts | reconstructs status markers and checkpoint |
| delta index | emits only missing/retryable manifest entries |
| run-dir reuse | resumed artifacts append to canonical run root |

Use stubs or fixtures for external tools so tests are deterministic.

## Minimal Verification

Run syntax/static checks for modified scripts, then the focused test subset. For shell workflows, include a stubbed end-to-end smoke test that verifies files, logs, and status markers.

## Documentation to Ship

Document these paths:

1. first run from a manifest
2. rerun with checkpoint after interruption
3. build missing-only manifest from artifacts
4. backfill older run artifacts
5. inspect failure snapshots and raw logs
6. tune pacing and retry settings
7. merge split run artifacts, if needed

Include exact command examples for each workflow in the target project’s native tooling.
