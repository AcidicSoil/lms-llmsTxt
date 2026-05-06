# State Evidence

Write compact artifacts so another agent can verify what happened without replaying the live browser session.

## Required Files

| File | Purpose |
|---|---|
| `custom-gpt-loop.summary.json` | Run outcome, counters, timings, and anomalies. |
| `.pinchtab/<profile>.instance_id` | Preserved browser instance pointer when PinchTab is used. |
| `.pinchtab/<profile>.tab_id` | Preserved tab pointer when PinchTab is used. |

## Summary Fields

Include: `workflow`, `target_url`, `profile`, `outcome`, `duration_ms`, `prompt_submitted`, `confirmation_count`, `denial_count`, `refresh_count`, `final_state`, `anomalies`, `artifact_version`, and UTC timestamps.

## Post-Run Check

After the loop exits, probe the saved tab or session once. Record whether the Custom GPT page is still readable. If teardown was required, state why and record the final known URL/state.
