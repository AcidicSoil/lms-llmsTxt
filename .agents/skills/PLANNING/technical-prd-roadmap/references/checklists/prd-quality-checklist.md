# PRD Quality Checklist

## Scope

- [ ] Problem statement is concrete.
- [ ] Target users and workflows are named.
- [ ] Success metrics are measurable.
- [ ] Non-goals are explicit.
- [ ] Assumptions are separated from facts.

## RPG Structure

- [ ] Capabilities describe behavior, not files.
- [ ] Features include description, inputs, outputs, and behavior.
- [ ] Modules have one responsibility.
- [ ] Public exports are listed.
- [ ] Dependencies are explicit and acyclic.
- [ ] Phases follow dependency order.

## Execution Readiness

- [ ] Each task has acceptance criteria.
- [ ] Each task has a test strategy.
- [ ] MVP produces a usable result.
- [ ] Risks include mitigation and fallback.
- [ ] Output artifacts and commands are named.

## Strict PRD Final Checks

- [ ] Output uses the exact 11-section order.
- [ ] Dependency chain includes explicit `Depends on: [...]` entries.
- [ ] Phase 0 contains only foundation modules with no dependencies.
- [ ] Final section recommends epic, task, and subtask counts with rationale.
