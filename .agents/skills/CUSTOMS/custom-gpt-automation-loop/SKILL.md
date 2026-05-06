---
name: custom-gpt-automation-loop
description: "Run ChatGPT Custom GPT browser loops with safe prompt scopes, tool-confirmation handling, stall recovery, session preservation, and evidence artifacts. WHEN: \"Custom GPT automation\", \"prompt loop\", \"tool confirmation\", \"Serena GPT\", \"ChatGPT browser loop\", \"refresh and reconfirm\"."
---

# Custom GPT Automation Loop

Use this when a signed-in browser workflow must repeatedly drive a ChatGPT Custom GPT and survive prompt submission, tool confirmations, streaming, idle stalls, refreshes, and preserved session state.

## Workflow

1. **Set the run contract** - Identify the GPT URL, signed-in profile, allowed prompt scope, forbidden actions, output directory, and stop conditions. For project-connected GPTs, load [Prompt Safety](references/prompt-safety.md).
2. **Attach to the live profile** - Prefer an existing signed-in profile or tab. Record profile, instance, and tab ids before issuing prompts.
3. **Discover the actual surface** - Try accessibility snapshots first. If they under-report ChatGPT content, use DOM inspection to locate the header, composer, ProseMirror editor, send control, streaming state, and interstitial buttons.
4. **Submit the smallest safe prompt** - Use a read-only or no-op prompt that exposes the required automation state without asking the GPT to edit files, run commands, or act on a connected project.
5. **Handle confirmations deterministically** - Detect tool-confirmation cards, confirm only allowlisted hosts/actions, deny unsafe calls, and continue only after the UI state changes. Load [Confirmation Recovery](references/confirmation-recovery.md).
6. **Watch for stuck loops** - Distinguish streaming text, completed answers, repeated tool-status lines, idle stalls, login loss, and stale tabs. Load [Watchdog Signals](references/watchdog-signals.md).
7. **Preserve and prove state** - Keep the live session open unless teardown is required. Write the summary artifact and session pointers described in [State Evidence](references/state-evidence.md).

## Completion Criteria

A loop pass is complete only when prompt submission, confirmation behavior, recovery count, final outcome, artifact contents, and post-run tab liveness have been inspected.
