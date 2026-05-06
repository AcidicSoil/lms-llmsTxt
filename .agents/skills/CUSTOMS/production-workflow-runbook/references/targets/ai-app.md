# AI App Runbook

## End State

AI product with bounded model behavior, strong UX, measurable quality, operational safeguards, and production monitoring.

## Critical Tracks

- product UX
- model/provider strategy
- prompt/system design
- retrieval/context engineering
- evaluation
- safety and abuse controls
- latency/cost controls
- observability
- fallback behavior

## Workflow

1. Define user jobs, model responsibilities vs deterministic code, trust boundaries, failure tolerance, quality bar, and unacceptable error classes.
2. Design provider abstraction, model choice, prompt contract, tool policy, context management, retrieval, memory, safety, structured outputs, human review points.
3. Establish eval harness, golden datasets, prompt/version management, tracing, cost/latency metrics, caching, moderation, fallbacks, audit logs where needed.
4. Build slices: user input/output loop, context/retrieval, tool invocation, citations/evidence, session history, feedback capture, admin controls.
5. Harden: hallucination tests, prompt-injection tests, jailbreak/abuse tests, retrieval precision/recall, schema adherence, timeouts, fallback, latency, cost guards.
6. Polish: credible progress states, clear uncertainty, visible evidence, easy retry/recovery, intentional input/output surfaces.

## Production Checklist

- eval suite tracked over time
- model changes gated by regression thresholds
- safety incidents observable
- latency/cost dashboards live
- prompt and model versions traceable
- retry/fallback strategy defined
- provider outage plan exists

## Brownfield Notes

Preserve deterministic system behavior around the model. Introduce AI features behind flags and compare outcomes with evals, not anecdotes.
