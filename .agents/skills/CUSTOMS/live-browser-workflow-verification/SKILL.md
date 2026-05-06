---
name: live-browser-workflow-verification
description: "Verify browser automation against live signed-in sessions with safety gating, DOM/snapshot fallback, confirmation handling, and evidence artifacts. WHEN: \"live browser test\", \"PinchTab verification\", \"signed-in session\", \"browser automation evidence\", \"confirm workflow\"."
---

# Live Browser Workflow Verification

Use this when a browser automation workflow must be proven against a real signed-in session, not only mocked DOM or unit tests.

## Workflow

1. **Set the live boundary** - Identify the exact URL, profile/session id, allowed prompt scope, and forbidden actions before touching the browser. For signed-in accounts, load [Safety Rules](references/safety.md).
2. **Probe before acting** - Check runtime health, active profile, current URL, and page readiness. Prefer accessibility snapshots first; fall back to DOM inspection only when snapshots under-report the interactive surface.
3. **Drive the smallest safe action** - Use the narrowest read-only or no-op prompt that can expose the target behavior. Avoid repo edits, shell commands, destructive UI actions, purchases, messages, or broad agent instructions unless explicitly requested.
4. **Handle interstitials deterministically** - Detect confirmation, deny, login, tool-call, streaming, and stale-tab states. For recovery patterns, load [Recovery Patterns](references/recovery.md).
5. **Preserve state unless teardown is required** - Keep live tabs/profiles open by default when session continuity is part of the verification target.
6. **Write evidence** - Emit a compact artifact with outcome, timings, submitted prompt flag, confirmation count, refresh count, anomalies, profile id, tab/session ids, and post-run liveness. Use [Evidence Contract](references/evidence.md).
7. **Report only verified facts** - Separate observed results from assumptions; include file paths, command names, and artifact summaries.

## Completion Criteria

A live verification pass is complete only when the run outcome, session state, recovery behavior, and evidence artifact have all been inspected after the workflow exits.
