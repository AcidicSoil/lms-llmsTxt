# Core Workflow

Use this sequence when converting a one-pass automation into a resumable artifact workflow.

## 1. Normalize Input

Accept a manifest in one or more shapes, then normalize to an ordered list:

- raw array: `[item, item]`
- wrapped export: `{ "schema_version": "...", "artifact_type": "...", "data": [...] }`
- named collection: `{ "items": [...] }`, `{ "projects": [...] }`, or domain equivalent

Extract a stable key for each item. Prefer immutable IDs or canonical URLs. Names are secondary metadata.

## 2. Create a Run Root

Use one run directory per campaign unless resuming with an existing checkpoint that points to a prior run.

Recommended layout:

```text
runs/<workflow>_<timestamp>/
  artifacts/<item-slug>/
    scan_status.json
    output.*
    logs/
    snapshots/
  checkpoints/<workflow>.tsv
```

## 3. Process One Item Safely

For each item:

1. write `started` status
2. execute stage 1
3. verify the next stage before proceeding
4. capture output or confirmed-empty state
5. write terminal status
6. append checkpoint row

A command being sent is not success. Verify the observable next state.

## 4. Resume

Before iterating, load completed keys from checkpoint and status markers. Skip terminal-success statuses. Keep failed, started-only, or unknown states eligible for retry.

## 5. Delta Runs

Build a local index from artifact status markers, compare it against the manifest, then write a reduced manifest containing only missing or retryable items.

Use this for interrupted runs, periodic sync, newly added manifest entries, and large workflows where reprocessing is expensive.
