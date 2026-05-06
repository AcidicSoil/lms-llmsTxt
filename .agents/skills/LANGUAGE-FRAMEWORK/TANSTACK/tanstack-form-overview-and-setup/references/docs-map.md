# TanStack Form Docs Map

## Read this when

- setting up TanStack Form for the first time
- deciding which TanStack Form skill or doc slice to use
- mapping a task to validation, dynamic fields, submission UX, composition, or React runtime work

## Top-level docs surfaces

- `Getting Started`: `Overview`, `Installation`, `Philosophy`, `Comparison`, `TypeScript`, and `Quick Start`
- `Guides`: `Basic Concepts`, `Form Validation`, `Dynamic Validation`, `Async Initial Values`, `Arrays`, `Linked Fields`, `Reactivity`, `Listeners`, `Custom Errors`, `Submission Handling`, `UI Libraries`, `Focus Management`, `Form Composition`, `React Native`, `SSR/TanStack Start/Next.js`, `Debugging`, and `Devtools`
- `API Reference`: `useForm`, `useField`, `useTransform`, `formOptions`, `mergeForm`, `FormApi`, `FieldApi`, validator interfaces, and deep-key types
- `Examples`: `Simple`, `Arrays`, `Form Composition`, `Dynamic Validation`, `TanStack Query Integration`, `Standard Schema`, `TanStack Start`, `Next Server Actions`, `Remix`, `UI Libraries`, `Field Errors From Form Validators`, and `Devtools`

## Recommended skill routing

- package choice, framework selection, TypeScript baseline, or docs topology -> `tanstack-form-overview-and-setup`
- field or form validators, timing, schemas, custom errors -> `tanstack-form-validation-and-errors`
- arrays, linked fields, subscriptions, or listeners -> `tanstack-form-dynamic-fields-and-reactivity`
- async initial values, submit metadata, focus-first-error UX -> `tanstack-form-data-loading-and-submission-ux`
- app-level form wrappers, custom field components, or UI-library binding -> `tanstack-form-composition-and-ui-integration`
- Next.js, TanStack Start, Remix, React Native, or devtools -> `tanstack-form-react-runtime-integrations`

## Framework notes

- The library is framework-agnostic, but the official guide depth is strongest on the React surface.
- Cross-framework package selection is still straightforward:
  - React -> `@tanstack/react-form`
  - Vue -> `@tanstack/vue-form`
  - Angular -> `@tanstack/angular-form`
  - Solid -> `@tanstack/solid-form`
  - Svelte -> `@tanstack/svelte-form`
  - Lit -> `@tanstack/lit-form`
- The core mental model stays consistent across adapters even when the entry API differs:
  - React and Vue -> `useForm`
  - Solid and Svelte -> `createForm`
  - Angular -> `injectForm` and `TanStackField`
  - Lit -> `TanStackFormController`

## Source map

- `https://tanstack.com/form/latest/docs`
- `https://tanstack.com/form/latest/docs/philosophy`
- `https://tanstack.com/form/latest/docs/typescript`
- `https://tanstack.com/form/latest/docs/framework/react/quick-start`
- `https://github.com/TanStack/form/releases`
