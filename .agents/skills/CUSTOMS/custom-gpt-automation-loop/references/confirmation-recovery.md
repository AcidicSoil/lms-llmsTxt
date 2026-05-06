# Confirmation Recovery

Custom GPT tool calls can pause behind an in-thread confirmation interstitial. Treat it as a state machine, not a string-matching afterthought.

## Detection

Confirm only after observing all available signals:

| Signal | Expected Evidence |
|---|---|
| Host line | Tool host or bridge endpoint is visible. |
| Tool-call line | Requested action is visible enough to classify. |
| Buttons | `Confirm` and `Deny` controls are present and enabled. |
| Thread context | The card belongs to the active prompt, not stale history. |

## Action Policy

1. Classify the host and action against the run contract.
2. Click `Confirm` only for allowlisted read-only behavior or explicitly authorized actions.
3. Click `Deny` or stop for unknown, destructive, or over-broad requests.
4. After clicking, wait for a concrete state transition: streaming starts, the card disappears, or an error appears.

## Recovery Path

If the loop stalls after confirmation, refresh the tab, reattach to the same session, rediscover the card, and reapply the same action policy. Count refreshes and confirmations separately in the evidence artifact.
