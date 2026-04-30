# Loader fetch discipline

- Fetch speculative data via TanStack Start loaders.
- Never use `useEffect` for server reads.

## Hydration + suspense safety

- Avoid suspending updates during hydration.
- Wrap synchronous updates that may suspend with `startTransition`.

## Zustand state syncing

- Keep server-synced data out of Zustand.
- Mirror server truth via TanStack DB collections instead.
