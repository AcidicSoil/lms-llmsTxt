# Consistency Checks

Run a small verification pass after documentation edits.

## Checks

| Check | Method |
|---|---|
| Command names | Compare docs to CLI parser/help/source |
| Flags and defaults | Compare docs to implementation defaults |
| Artifact names | Compare docs to emitted files or schema code |
| Links | Verify local markdown targets exist |
| Examples | Ensure commands are copy-pasteable and paths are real |
| TODO state | Ensure completed/open statuses match verified work |
| Terminology | Use one name for each command, artifact, and runtime concept |

## Report Format

Return:

1. docs changed
2. behavior now documented
3. consistency checks performed
4. files intentionally not touched
5. unresolved gaps, if any

## Failure Handling

If a check contradicts the proposed docs, stop and either patch the docs back to source truth or report that implementation and docs disagree. Do not leave known drift in place.
