---
name: terminal-ux-specification
description: "Turn CLI design preferences into reusable product/spec language. WHEN: \"CLI style\", \"terminal UX\", \"ANSI-styled output\", \"command-line design\", \"modern CLI\"."
---

# Terminal UX Specification

## Workflow

1. Convert informal CLI design preferences into a reusable specification.\n2. Describe output structure, semantic color use, spacing, alignment, tables, borders, and help screens.\n3. Keep the spec language implementation-neutral.\n4. State that the tool should remain a standard command-line interface unless a TUI is explicitly requested.

## Output Requirements

- Use language-agnostic terminology unless the user specifies a stack.
- Distinguish standard CLI output from full-screen TUIs.
- Prefer concise, implementation-ready language.
- Include the phrase "modern terminal-native CLI with structured, ANSI-styled output" when it fits.
