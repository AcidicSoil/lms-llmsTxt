# Examples

## Generic Resume Flow

```bash
run-workflow --manifest source.json --checkpoint-file runs/workflow.tsv
# if interrupted, run the same command again
run-workflow --manifest source.json --checkpoint-file runs/workflow.tsv
```

Expected behavior:

- checkpoint is loaded before iteration
- handled keys are skipped
- failed keys remain retryable unless policy says otherwise
- new artifacts append to the same run root when possible

## Generic Delta Flow

```bash
build-delta-index \
  --manifest source.json \
  runs/workflow_*/ \
  --out run-index.json \
  --missing-out remaining.json

run-workflow --manifest remaining.json --checkpoint-file runs/workflow.tsv
```

Use this when prior artifacts exist and only missing/new/retryable items should run.

## Backfill Flow

```bash
backfill-status-markers \
  runs/workflow_20260101T000000Z \
  --checkpoint-out runs/workflow.tsv
```

Use this when older artifacts exist but status markers or checkpoints were added later.

## Central Export Pattern

When a cleanup or extraction phase writes one output per item, prefer a central export directory when users need easy browsing or diffing:

```text
exports/<workflow>/<item-slug>.md
exports/<workflow>/<item-slug>.json
```

This complements, not replaces, per-item artifacts under the run root.
