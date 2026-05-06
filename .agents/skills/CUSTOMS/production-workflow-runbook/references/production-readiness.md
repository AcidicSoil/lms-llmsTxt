# Production Readiness

Apply these gates to every target.

## Product Gate

- primary user journey complete
- edge states present
- onboarding or first-run path acceptable
- UX reviewed against target users
- polish debt known and acceptable

## Engineering Gate

- lint, format, typecheck, tests green
- critical defects closed
- config and secrets sane
- observability in place
- rollback path tested
- local dev path documented

## Security Gate

- authentication and authorization verified where relevant
- secret handling correct
- dependency and license review complete
- abuse paths reviewed
- privacy/compliance requirements satisfied or marked out of scope

## Operations Gate

- deploy documented
- staged/canary release path available where relevant
- dashboards live
- alerts actionable
- backup/recovery plan exists where data is durable
- incident and support runbooks exist

## Business Gate

- success metrics instrumented
- release notes prepared
- owner assigned
- support path known
- launch decision recorded

## Definition of Done

A runbook is complete when it defines:
- phases from intake through post-launch
- required artifacts
- target-specific implementation tracks
- brownfield or greenfield risks
- verification checks
- polish criteria
- production-readiness gates
- launch and rollback process
