# Functional and Structural Decomposition

## Functional Decomposition

Start with capabilities: what the system must do. For each feature, specify:

| Field | Meaning |
|---|---|
| Description | One-sentence purpose |
| Inputs | Data, files, state, or context required |
| Outputs | Artifacts, return values, UI state, or side effects |
| Behavior | Key logic and transformation rules |

Good capability names are user- or system-behavior oriented: `Prompt Inventory`, `Eval Execution`, `Promotion Review`.

## Structural Decomposition

After capabilities are clear, map them to repository structure:

```text
project-root/
├── src/module-name/
│   ├── feature-one.ts
│   ├── feature-two.ts
│   └── index.ts
└── tests/module-name/
```

Each module definition should include:

- mapped capability
- single responsibility
- file structure
- public exports
- integration points

## Quality Check

If a feature cannot be tested independently, it is probably too broad. If a module needs unrelated responsibilities, split it.
