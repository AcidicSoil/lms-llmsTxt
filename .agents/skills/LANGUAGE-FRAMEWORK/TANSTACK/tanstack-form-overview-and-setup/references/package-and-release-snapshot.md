# Package And Release Snapshot

## Framework packages

- React: `@tanstack/react-form`
- Vue: `@tanstack/vue-form`
- Angular: `@tanstack/angular-form`
- Solid: `@tanstack/solid-form`
- Svelte: `@tanstack/svelte-form`
- Lit: `@tanstack/lit-form`

## React runtime packages

- Next.js App Router and Server Actions: `@tanstack/react-form-nextjs`
- Remix: `@tanstack/react-form-remix`
- TanStack Start: `@tanstack/react-form-start`
- React devtools: `@tanstack/react-devtools`
- Form devtools plugin: `@tanstack/react-form-devtools`
- Shared devtools package: `@tanstack/form-devtools`

## Verified release snapshot

- Docs site currently labels the library as `Form v1`.
- Official GitHub releases show `@tanstack/react-form@1.28.5` on 2026-03-12.
- The same release batch covers the React meta-framework adapters documented in the SSR guides and examples.
- Official GitHub releases show form devtools packages at `0.2.19` on 2026-03-15.

## TypeScript baseline

- `strict: true` is required for the intended type experience.
- TypeScript `5.4+` is required.
- Official docs recommend locking the TanStack Form package to a specific patch version because type improvements can ship in patch releases.
- Prefer inference from runtime `defaultValues` instead of passing manual form generics.

## Source map

- `https://tanstack.com/form/latest/docs/typescript`
- `https://tanstack.com/form/latest/docs/philosophy`
- `https://github.com/TanStack/form/releases`
