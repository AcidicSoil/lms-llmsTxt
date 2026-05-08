# Testing and Architecture

## Test Strategy

Use a test pyramid:

| Test Type | Role |
|---|---|
| Unit | Fast validation of pure logic and edge cases |
| Integration | Module boundaries, IO, persistence, providers |
| E2E | Critical user flow or CLI/API path |

For each module, include happy path, edge cases, error cases, and integration points.

## Architecture Section

Place architecture after functional and structural decomposition. Include:

- system components
- data models
- APIs and integrations
- infrastructure requirements
- key decisions with rationale, trade-offs, and alternatives

## Decision Format

```text
Decision: [Pattern or technology]
Rationale: [Why]
Trade-offs: [Cost]
Alternatives considered: [Rejected options]
```
