# API Service Runbook

## End State

Reliable service with clear contracts, observability, safe deployment, and manageable operational characteristics.

## Critical Tracks

- domain and contract design
- storage/data integrity
- authentication and authorization
- performance/scaling
- resilience
- observability
- deployment and rollback

## Workflow

1. Define resources, operations, error model, idempotency, auth model, quotas, rate limits, and versioning policy.
2. Design service boundaries, persistence, queues/jobs, consistency guarantees, caching, migrations, and deployment topology.
3. Establish schema management, migrations, CI/CD, tests, health checks, logs, metrics, traces, secrets/config, local dev.
4. Build slices: health/version/auth, primary resource CRUD, async processing, admin/ops paths, rate limiting/quota, reporting surfaces.
5. Harden: load tests, migration rollback, authz tests, timeout/circuit breakers, retries, idempotency, partial failure, regional/network assumptions.
6. Polish: consumer-grade docs, consistent errors, SDKs/examples where needed, simple local/staging workflows.

## Production Checklist

- OpenAPI or equivalent current
- migration plan proven
- canary deploy path proven
- dashboards and alerts live
- SLOs or practical thresholds defined
- incident runbook exists
- backup and data retention policy defined

## Brownfield Notes

Preserve existing contracts. Version breaking changes. Use adapters, shadow reads, dual writes, or compatibility layers during migrations.
