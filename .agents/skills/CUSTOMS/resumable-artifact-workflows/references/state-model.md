# State Model

Use explicit item state rather than inferring completion from directory existence.

## Statuses

| Status | Meaning | Count as handled? |
|---|---|---|
| `started` | Item began but has no terminal result | No |
| `captured` | Output was captured and contains meaningful content | Yes |
| `captured_empty` | Target was reached and verified empty | Yes |
| `failed_before_stage` | Could not reach required next stage | No |
| `failed_no_output_found` | Stage was reached but expected output never appeared | No |
| `failed_blocked` | Workflow encountered a blocker, modal, auth wall, rate limit, or similar | No |

Rename statuses to fit the domain, but preserve the success-vs-retry split.

## Status Marker Fields

Each artifact directory should include `scan_status.json` or equivalent:

```json
{
  "status": "captured",
  "item_key": "stable-id-or-url",
  "item_name": "Human label",
  "started_at": "2026-01-01T00:00:00Z",
  "updated_at": "2026-01-01T00:05:00Z",
  "artifact_path": "runs/.../artifacts/item/output.md",
  "failure_snapshot_path": null,
  "message": "optional human summary"
}
```

## Checkpoint Rows

Use append-only rows so failures are auditable:

```text
status<TAB>item_key<TAB>timestamp<TAB>detail
completed<TAB>https://example/item/1<TAB>20260101T000500Z<TAB>runs/.../output.md
failed<TAB>https://example/item/2<TAB>20260101T000700Z<TAB>failed_before_stage
```

Only the latest terminal row for a key should control resume behavior. Prefer completed/captured states over older failed rows.

## Backfill Rules

When older runs lack status markers:

1. resolve item key from logs, command trace, metadata, or output header
2. classify confirmed outputs as `captured`
3. classify confirmed empty outputs as `captured_empty`
4. classify artifact directories without terminal output as failed or unresolved
5. write markers and regenerate checkpoint from the canonical run root
