# Library SDK Runbook

## End State

Stable library with coherent API design, version discipline, examples, docs, and confidence across supported environments.

## Critical Tracks

- API ergonomics
- backwards compatibility
- packaging
- test matrix
- docs/examples
- performance
- deprecation policy

## Workflow

1. Define public surface, internal modules, extension points, sync/async behavior, errors, and configuration strategy.
2. Establish package metadata, semantic versioning, CI matrix, docs structure, examples, and benchmark harness if needed.
3. Build slices: core primitives, common workflows, integration helpers, config/auth, examples, migration docs.
4. Harden: dependency compatibility, public API snapshots, performance regressions, docs accuracy, supported runtime versions.
5. Polish: excellent getting started, real examples, useful errors, minimal public surface, clear upgrade guidance.

## Production Checklist

- public API documented
- versioning and deprecation policy documented
- release automation defined
- compatibility matrix defined
- examples tested in CI
- package signing/provenance considered where relevant
- changelog generated or maintained

## Brownfield Notes

Preserve public API. Deprecate before removal. Provide codemods or migration notes for major upgrades. Avoid accidental exports.
