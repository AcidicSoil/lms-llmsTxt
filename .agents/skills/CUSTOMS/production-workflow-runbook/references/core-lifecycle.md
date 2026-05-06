# Core Lifecycle

Use this lifecycle for every production workflow runbook.

## Phase 0 — Intake

Capture problem, users, business goal, target platform, brownfield/greenfield status, constraints, success metrics, and non-goals.

Artifacts: `PROJECT.md`, `REQUIREMENTS.md`, `NON_GOALS.md`, `RISKS.md`, `SUCCESS_METRICS.md`.

Exit: scope, users, finish line, and measurable success criteria are explicit.

## Phase 1 — Discovery and Baseline

Greenfield: validate problem, references, technical feasibility, information architecture, and platform choice.

Brownfield: inventory repo, dependencies, runtime topology, data flows, deployment path, UX quality, test coverage, observability, and defects.

Exit: major unknowns and risk hotspots are documented.

## Phase 2 — Product and System Design

Define architecture, domain model, API contracts, state model, UX flows, component inventory, release slices, and acceptance criteria.

Exit: each requirement maps to an implementation path and verification method.

## Phase 3 — Foundation

Establish repo structure, build tooling, CI, lint/typecheck/test harness, config, secrets, logging, metrics, error reporting, auth skeleton, design primitives, feature flags, and release mechanism.

Exit: trunk builds, tests, and deploys from documented commands.

## Phase 4 — Vertical Slices

For each slice: acceptance criteria, failing check, implementation, UX, analytics, logs, empty/loading/error states, accessibility/performance/security review, docs.

Exit: happy path and failure states work end-to-end.

## Phase 5 — Integration Hardening

Verify auth, data migrations, concurrency, third-party integrations, retries, idempotency, rate limits, degraded networks, backward compatibility, and platform matrix.

Exit: top operational and integration risks are directly tested.

## Phase 6 — Polish

Refine visual consistency, interaction quality, copy, onboarding, accessibility, responsiveness, keyboard support, performance, and help surfaces.

Exit: product feels intentional, not merely functional.

## Phase 7 — Production Readiness

Validate CI, tests, staged deploy, rollback, dashboards, alerts, runbooks, release notes, security, privacy, dependency review, and support ownership.

Exit: the system can be operated and recovered.

## Phase 8 — Launch and Learn

Stage rollout, monitor KPIs/errors, collect feedback, patch issues, and split stabilization from next-wave work.
