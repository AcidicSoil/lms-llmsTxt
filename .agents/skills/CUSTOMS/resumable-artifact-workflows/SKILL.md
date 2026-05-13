---
name: resumable-artifact-workflows
description: "Design resilient artifact-producing automation with checkpoint/resume, delta indexing, backfill, retries, status markers, failure snapshots, and docs. WHEN: \"make this script resumable\", \"add checkpointing\", \"index processed items\", \"resume automation\", \"backfill artifacts\", \"harden this workflow\"."
---

# Resumable Artifact Workflows

Use this skill to harden any batch workflow that reads a manifest, processes many items, and writes local artifacts.

## Core Procedure

1. **Identify durable identity** - Choose a stable key per manifest item: URL, ID, path, slug, or checksum. Do not depend on display names alone.
2. **Define run layout** - Store outputs under one run root with per-item artifact directories, logs, snapshots, and status markers.
3. **Add checkpoint/resume** - Record completed and failed item keys as the run progresses. Load the checkpoint before iterating.
4. **Build delta indexing** - Compare the source manifest against local status markers to emit a remaining-items manifest.
5. **Backfill older runs** - Reconstruct status markers and checkpoint rows from existing artifacts before rerunning from scratch.
6. **Harden fragile steps** - Add pacing, retries, next-stage verification, concise terminal output, and raw logs.
7. **Verify behavior** - Add tests for delayed success, failure before completion, resume skipping, backfill, and delta output.

## Read Details As Needed

- For the full reusable algorithm, read [Core Workflow](references/core-workflow.md).
- For statuses, checkpoints, indexes, and backfill rules, read [State Model](references/state-model.md).
- For retry, pacing, logging, and failure snapshots, read [Observability](references/observability.md).
- For implementation validation, read [Testing and Docs](references/testing-and-docs.md).
- For portable examples and templates, read [Examples](references/examples.md).

## Bundled Templates

Use [status-marker.json](templates/status-marker.json), [checkpoint.tsv](templates/checkpoint.tsv), and [run-layout.md](templates/run-layout.md) as starting points.

## Optional Helper

Use `scripts/delta_index.py` when a generic manifest-vs-artifact delta indexer is enough. Adapt key extraction and status parsing to the target project.
