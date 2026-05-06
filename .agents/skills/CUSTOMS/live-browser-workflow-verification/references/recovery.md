# Recovery Patterns

Use this when the live browser pass encounters interstitials, stale state, or missing accessibility data.

## Detection Matrix

| State | Signal | Action |
|---|---|---|
| Snapshot under-reports page | Header visible in DOM but not accessibility tree | Inspect DOM for composer, buttons, role attributes, and text labels. |
| Tool confirmation | In-thread host/tool line plus Confirm/Deny buttons | Record confirmation count; click only if the prompt scope is safe and user-approved. |
| Login/MFA wall | Sign-in, password, or verification prompt | Stop. Do not enter credentials or bypass MFA. |
| Streaming response | Stop/regenerate controls or changing message text | Poll until stable before judging outcome. |
| Stale tab/session | Saved tab id no longer resolves | Attempt one refresh or reattach; record refresh count and anomaly. |
| Forced teardown regression | Workflow closes client in finally path | Add a no-close option/default for live verification and test post-run liveness. |

## Recovery Rules

1. Prefer reattach over opening a new tab so state continuity is testable.
2. Limit refresh recovery to one bounded attempt unless the user asked for stress testing.
3. Never silently continue after a permission boundary changes.
4. Always record recovery actions in the evidence artifact.
