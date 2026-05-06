---
name: runtime-docs-sync
description: "Sync repository docs after verified runtime or CLI behavior changes by mapping source-of-truth code, updating owned docs surfaces, TODOs, artifact contracts, and consistency checks. WHEN: \"update docs\", \"sync docs\", \"docs drift\", \"runtime behavior changed\", \"CLI reference update\", \"artifact contract update\"."
---

# Runtime Docs Sync

Use this when implementation, CLI behavior, runtime artifacts, or validated live-system behavior has changed and repository docs must be updated without introducing drift.

## Workflow

1. **Anchor on verified behavior** - Collect the command surface, emitted artifacts, runtime logs, test output, and live-run evidence before editing. Use [Runtime Evidence](references/runtime-evidence.md) when behavior came from a live loop, CLI run, or generated artifact.
2. **Map owned doc surfaces** - Find existing README, CLI reference, runtime notes, artifact contracts, plans, and TODO files. Do not create a new top-level doc unless no owned surface exists. Use [Source Surface Map](references/source-surface-map.md).
3. **Patch narrowly** - Update only the sections that correspond to verified behavior: flags, defaults, outputs, artifact names, runtime boundaries, and plan status. Use [Sync Patch Rules](references/sync-patch-rules.md).
4. **Sync plans and TODOs** - Mark completed work as done only when implementation and verification evidence exist. Preserve open items that remain unimplemented.
5. **Run consistency checks** - Compare docs against source names, flags, output paths, artifact schemas, examples, and links. Use [Consistency Checks](references/consistency-checks.md).
6. **Report the diff** - List changed docs, what each now covers, checks performed, and any intentionally untouched files or unresolved gaps.

## Completion Criteria

A docs sync is complete only when the updated docs point to existing behavior, plan/TODO state matches implementation reality, artifact contracts match emitted files, and a final consistency pass has been reported.
