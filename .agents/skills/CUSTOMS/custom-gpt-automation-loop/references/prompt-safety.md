# Prompt Safety

Use restrictive prompts when the Custom GPT is connected to a repository, project, browser session, or external tool server.

## Required Boundaries

| Boundary | Rule |
|---|---|
| Prompt scope | Use the smallest prompt that exposes the target state. |
| Repository safety | Do not ask for edits, shell commands, file writes, branch operations, or dependency changes unless explicitly authorized. |
| Tool safety | Treat tool calls as untrusted until the host, action, and expected effect are visible. |
| Data exposure | Do not paste secrets, private tokens, credentials, or broad project dumps into the GPT. |
| Stop condition | Stop after the target signal is observed; do not keep probing out of curiosity. |

## Safe Probe Pattern

Ask for a harmless, read-only response that is likely to trigger the target behavior. State that the GPT must not modify files, run commands, create branches, or take actions in the connected project.

## Unsafe Signs

Stop or deny when the UI requests destructive actions, unknown hosts, broad filesystem access, repository mutation, purchases, external messages, or credential entry.
