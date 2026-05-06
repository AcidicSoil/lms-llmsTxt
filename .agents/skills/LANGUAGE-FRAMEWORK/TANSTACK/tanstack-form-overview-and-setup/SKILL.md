---
name: tanstack-form-overview-and-setup
description: Set up TanStack Form, choose the correct framework or runtime package, and route TanStack Form work to the right follow-up skill. Use whenever tasks mention `@tanstack/*-form`, `useForm`, `createForm`, `injectForm`, `TanStackFormController`, installation, TypeScript setup, version selection, or deciding whether a task belongs to validation, dynamic fields, submission UX, composition, or React runtime integrations.
---

# TanStack Form Overview and Setup

Use this skill when the task is primarily about onboarding, package selection, docs routing, or version and TypeScript guardrails.

## Scope

- docs topology and skill routing
- framework package selection
- install and first-time setup choices
- philosophy and TypeScript baseline
- release snapshot awareness before deeper implementation work

## Routing cues

- install TanStack Form, pick the right package, understand the docs, compare adapters, or decide where a task belongs -> use this skill
- validator timing, Standard Schema, custom errors, or `disableErrorFlat` -> use `tanstack-form-validation-and-errors`
- arrays, linked fields, `form.Subscribe`, `useStore`, or listeners -> use `tanstack-form-dynamic-fields-and-reactivity`
- TanStack Query hydration, `onSubmitMeta`, `onSubmitInvalid`, or focus-first-error UX -> use `tanstack-form-data-loading-and-submission-ux`
- `createFormHook`, `withForm`, `withFieldGroup`, `useFieldContext`, or UI library adapters -> use `tanstack-form-composition-and-ui-integration`
- Next.js, Remix, TanStack Start, React Native, `mergeForm`, `useTransform`, or devtools -> use `tanstack-form-react-runtime-integrations`

## Workflow

1. Read [references/docs-map.md](./references/docs-map.md) first.
2. If the task mentions packages, versions, or framework choice, read [references/package-and-release-snapshot.md](./references/package-and-release-snapshot.md).
3. If the task is broad, use [references/coverage-matrix.md](./references/coverage-matrix.md) to route to the owning skill before editing code.
4. Keep setup decisions minimal and aligned with the framework and runtime already in use.

## Quick example

```bash
# Choose the adapter that matches your framework
npm install @tanstack/react-form
# npm install @tanstack/vue-form
# npm install @tanstack/angular-form
```

## Guardrails

- Treat TanStack Form as controlled-first and headless; the library owns form state, while the app owns rendering, accessibility details, and focus behavior.
- Prefer inference from `defaultValues` instead of manually supplying form generics.
- Keep the framework package aligned with the actual renderer:
  - React -> `@tanstack/react-form`
  - Vue -> `@tanstack/vue-form`
  - Angular -> `@tanstack/angular-form`
  - Solid -> `@tanstack/solid-form`
  - Svelte -> `@tanstack/svelte-form`
  - Lit -> `@tanstack/lit-form`
- React meta-framework work belongs to the runtime skill because package imports change for Next.js, Remix, and TanStack Start.

## Maintenance

- Snapshot date: 2026-03-24
- Docs snapshot: official TanStack Form docs `Form v1`
- Release snapshot: `@tanstack/react-form@1.28.5` and related React runtime adapters on 2026-03-12; form devtools `0.2.19` on 2026-03-15

## References

- [references/docs-map.md](./references/docs-map.md)
- [references/package-and-release-snapshot.md](./references/package-and-release-snapshot.md)
- [references/coverage-matrix.md](./references/coverage-matrix.md)
