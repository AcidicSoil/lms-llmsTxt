# Dependencies and Phases

## Dependency Chain

List modules in build order. Foundation modules come first and have no dependencies.

```text
Foundation Layer
- config: Depends on []
- schemas: Depends on []

Data Layer
- parser: Depends on [schemas]
- store: Depends on [schemas, config]

Workflow Layer
- runner: Depends on [parser, store]
```

## Phase Rules

Each phase should contain tasks that can be worked in parallel. Avoid placing task B in the same phase if it depends on task A.

Each phase needs:

- goal
- entry criteria
- tasks with dependencies
- acceptance criteria
- test strategy
- exit criteria
- delivered capability

## Usability Bias

Do not build infrastructure forever. Design phases so the first usable vertical slice appears as early as possible, even if it is narrow.
