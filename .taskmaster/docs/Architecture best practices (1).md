
* Define clear domain boundaries; hide internals behind interfaces.

* One responsibility per module; no god objects.

* Depend on abstractions, not concretions (DIP).

* Enforce layering; no upward or cross-layer calls.

* Use anti-corruption layers at external boundaries.

* Make core logic pure; push side effects to the edges.

* Prefer immutability; minimize shared mutable state.

* No global state; use dependency injection.

* Stable, versioned contracts (OpenAPI/Proto); never break consumers.

* Backward compatibility first; deprecate with policy and timelines.

* Idempotent operations; safe retries.

* Timeouts, retries with backoff, and circuit breakers on all I/O.

* Transactional integrity; use outbox/inbox for cross-service side effects.

* Single source of truth per data domain; explicit ownership.

* Version and migrate schemas; migrations are reversible and tested.

* Pagination and limits on every list API; no unbounded responses.

* Security by default: least privilege, secret management, input validation.

* Configuration is externalized and environment-based; no config in code.

* Deterministic builds and deploys; lockfiles and pinned toolchains.

* CI gates merges with fast, reliable tests (unit, integration, contract).

* Observability built-in: structured logs, metrics, traces with exemplars.

* Feature flags for risky changes; support dark launches and gradual rollout.

* Zero-downtime deploys with rollback plans; data changes are forward-compatible.

* Document architecture decisions (ADRs) and keep high-signal READMEs current.

---

Where to adapt, not drop:

* Frontend apps: apply boundaries by feature/domain; DI becomes composition; API contracts still versioned.

* ML systems: purity for data/feature code; model I/O is a boundary; add lineage and reproducibility to “observability.”

* Data pipelines: idempotency and exactly-once > transactions; schemas and backfills are versioned and reversible.

* Real-time/embedded: timeouts/circuit breakers tune to hard latency; immutability balanced with memory constraints.

* Small scripts/toys: scale down formality, keep “no globals,” tests, and ADRs-lite.

* Highly regulated: add audit trails and explicit change control to the list.

Rule of thumb: never violate the principle, only tailor its implementation.

---
