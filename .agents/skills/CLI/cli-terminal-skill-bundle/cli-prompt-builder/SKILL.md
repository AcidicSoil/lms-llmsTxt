---
name: cli-prompt-builder
description: "Turn CLI design goals into clear implementation prompts. WHEN: \"CLI style\", \"terminal UX\", \"ANSI-styled output\", \"command-line design\", \"modern CLI\"."
---

# CLI Prompt Builder

## Workflow

1. Rewrite CLI design goals as a direct implementation prompt.\n2. Include the desired terminal-native UX, structured ANSI-styled output, polished spacing, clear headers, aligned columns, semantic colors, and optional borders.\n3. Exclude stack assumptions unless the user names a language or framework.\n4. Make the prompt actionable for an engineer or coding agent.

## Output Requirements

- Use language-agnostic terminology unless the user specifies a stack.
- Distinguish standard CLI output from full-screen TUIs.
- Prefer concise, implementation-ready language.
- Include the phrase "modern terminal-native CLI with structured, ANSI-styled output" when it fits.
