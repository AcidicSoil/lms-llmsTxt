# Web App Runbook

## End State

Responsive, accessible, polished web product with stable deployment, analytics, and supportable operations.

## Critical Tracks

- product and UX
- frontend architecture
- backend/API integration
- auth/session
- performance
- accessibility
- analytics
- deployment

## Workflow

1. Define personas, core journeys, navigation, public/authenticated surfaces, browser/device support.
2. Design information architecture, wireframes, component system, forms, validation, tables, search, settings, empty/loading/error states.
3. Establish rendering model, state model, API boundaries, auth/session handling, caching/data-fetch strategy, CI/CD, preview environments.
4. Build slices: shell/navigation, auth, dashboard, primary object list/detail/create/edit, search/filter/sort, settings, notifications/help.
5. Harden: accessibility audit, performance pass, form validation pass, browser matrix, auth expiry, analytics verification, SEO if public, error boundaries.
6. Polish: visual consistency, microcopy, responsive layout, restrained animation, keyboard navigation, skeletons, onboarding.

## Production Checklist

- p95 route load and interaction targets set
- error tracking integrated
- traffic/error/funnel dashboards live
- privacy/cookie handling if required
- robots/sitemap/metadata if public
- CDN/cache settings sane
- rollback deploy path proven

## Brownfield Notes

Preserve URLs, SEO metadata, analytics continuity, auth/session behavior, and core workflows. Replace legacy pages behind flags or route-level migrations.
