# Safety Rules for Live Signed-In Browser Sessions

Use these rules before prompting or clicking inside a real authenticated browser profile.

## Boundary Checklist

| Boundary | Required decision |
|---|---|
| Account | Confirm which signed-in profile/session is being used. |
| URL | Target only the supplied URL or explicitly approved domain. |
| Prompt scope | Make the prompt read-only unless the user approved state changes. |
| Workspace | Treat connected projects/repos as live production context. |
| Persistence | Preserve profile cookies, tab ids, and instance ids unless teardown is requested. |

## Safe Prompt Pattern

Use short prompts that ask for harmless introspection only:

```text
Read-only check: identify whether this interface is reachable. Do not edit files, run commands, create resources, send messages, or change project state.
```

For tool-confirmation tests, the prompt must trigger the smallest confirmation surface possible. Do not ask the remote agent to modify a repo, install packages, call external services, or perform broad autonomous work.

## Stop Conditions

Stop and report if the page requests payment, credentials, MFA, broad project permission, destructive confirmation, or access outside the approved URL/profile boundary.
