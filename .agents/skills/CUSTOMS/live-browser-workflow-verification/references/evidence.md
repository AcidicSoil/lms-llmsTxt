# Evidence Contract

Every live browser verification should write a machine-readable summary and inspect it before reporting success.

## Required Summary Fields

| Field | Meaning |
|---|---|
| `workflow` | Stable workflow name, e.g. `serena-loop`. |
| `outcome` | `completed`, `blocked`, `failed`, or `partial`. |
| `started_at` / `finished_at` | ISO timestamps or another parser-safe format. |
| `duration_ms` | Non-zero elapsed runtime when a run started and ended. |
| `prompt_submitted` | Whether the automation actually submitted input. |
| `confirmation_count` | Number of confirmation interstitials observed. |
| `refresh_count` | Number of refresh or reattach recoveries. |
| `anomalies` | Array of unexpected states, errors, or assumptions. |
| `profile_id` | Browser profile/session identifier when available. |
| `tab_id` / `instance_id` | Saved live-session handles when available. |
| `post_run_liveness` | Whether the tab/session was still usable after exit. |

## Report Format

Include:

1. Output directory and artifact path.
2. Outcome and elapsed time.
3. Whether a prompt was submitted.
4. Confirmation/recovery counts.
5. Post-run liveness result.
6. Any anomalies or unverified assumptions.

Do not claim success from command exit alone. Success requires inspecting the artifact and probing the live session after the workflow exits.
