---
name: developer-design-vocabulary
description: "Translate screenshots or examples into clear engineering terminology. WHEN: \"CLI style\", \"terminal UX\", \"ANSI-styled output\", \"command-line design\", \"modern CLI\"."
---

# Developer Design Vocabulary

## Workflow

1. Inspect the example or description for reusable visual and interaction patterns.\n2. Translate design cues into engineering terms: ANSI styling, box drawing, tabular layout, semantic color, command syntax highlighting, and help text hierarchy.\n3. Avoid naming a specific framework unless the user requests implementation details.\n4. Return vocabulary the user can paste into an issue, PRD, or implementation prompt.

## Output Requirements

- Use language-agnostic terminology unless the user specifies a stack.
- Distinguish standard CLI output from full-screen TUIs.
- Prefer concise, implementation-ready language.
- Include the phrase "modern terminal-native CLI with structured, ANSI-styled output" when it fits.
