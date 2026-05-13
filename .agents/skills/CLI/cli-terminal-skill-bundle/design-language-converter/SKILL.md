---
name: design-language-converter
description: "Convert visual or terminology notes into developer-ready prompts. WHEN: \"CLI style\", \"terminal UX\", \"ANSI-styled output\", \"command-line design\", \"modern CLI\"."
---

# Design Language Converter

## Workflow

1. Extract the reusable design intent from notes, screenshots, or terminology discussions.\n2. Convert that intent into concise developer-facing language.\n3. Preserve constraints such as language-agnostic implementation and standard CLI behavior.\n4. Provide copy-ready prompts, specs, or vocabulary depending on the user's requested format.

## Output Requirements

- Use language-agnostic terminology unless the user specifies a stack.
- Distinguish standard CLI output from full-screen TUIs.
- Prefer concise, implementation-ready language.
- Include the phrase "modern terminal-native CLI with structured, ANSI-styled output" when it fits.
