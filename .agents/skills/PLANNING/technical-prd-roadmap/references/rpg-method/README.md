# RPG Quick Guide

Repository Planning Graph (RPG) PRDs separate functional planning from structural planning, then connect them with explicit dependencies.

## Core Pattern

| Layer | Question | Output |
|---|---|---|
| Overview | Why does this matter? | Problem, users, success metrics |
| Functional decomposition | What does the system do? | Capabilities and features |
| Structural decomposition | Where does it live? | Modules, files, exports |
| Dependency graph | What must exist first? | Topological build order |
| Roadmap | How is it built safely? | Phases, tests, exit criteria |

## Rules

- Capabilities are not files. Name behaviors like `Data Validation`, not `validation.js`.
- Every feature needs description, inputs, outputs, and behavior.
- Every module has one responsibility and explicit exports.
- Foundation modules have no dependencies.
- Non-foundation modules depend on named earlier modules.
- If two modules depend on each other, split one or introduce a lower-level shared module.

## Related Sections

- [Functional and structural decomposition](functional-structural.md)
- [Dependencies and phases](dependencies-phases.md)
- [Testing and architecture](testing-architecture.md)
