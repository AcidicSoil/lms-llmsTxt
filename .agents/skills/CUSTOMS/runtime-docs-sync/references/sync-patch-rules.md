# Sync Patch Rules

Use this while editing docs after runtime or CLI behavior changes.

## Patch Scope

Update only facts tied to verified behavior:

- command names and subcommands
- flags, defaults, and teardown behavior
- generated artifact names and schema fields
- runtime/session boundaries
- recovery and confirmation behavior
- setup prerequisites that were validated
- TODO or plan status backed by implementation evidence

## Style Rules

1. Keep README content concise and task-oriented.
2. Put exhaustive options in reference docs, not quickstarts.
3. Put emitted file details in artifact contracts.
4. Put operational caveats in runtime notes.
5. Keep TODOs factual: done, open, blocked, or deferred.
6. Avoid broad rewrites unless the existing structure is wrong.

## Safety Rules

- Do not mark work done from docs alone.
- Do not remove open questions unless source evidence resolves them.
- Do not change unrelated UI plans, product plans, or local config notes unless they are stale because of this runtime change.
