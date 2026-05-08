# Task Master Handoff

Use RPG structure when the PRD will be parsed into implementation tasks.

## Parsing-Friendly Rules

| PRD Element | Task Master Use |
|---|---|
| `### Capability:` | Top-level task |
| `#### Feature:` | Subtask |
| `Depends on: [x, y]` | Task dependency graph |
| Phase number | Priority and execution order |
| Test strategy | Test generation context |

## Dependency Hygiene

- Use stable module names in dependency lists.
- Avoid vague dependencies like `everything`, `API`, or `backend`.
- Do not create circular dependencies.
- Keep features atomic enough to test.
- Put shared contracts, schemas, config, and error handling in foundation layers.

## Output Target

A good handoff PRD can be parsed into topological tasks without needing the parser to guess build order.
