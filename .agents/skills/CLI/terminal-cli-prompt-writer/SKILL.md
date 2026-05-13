---
name: terminal-cli-prompt-writer
description: "Turn rough notes into polished prompts, design briefs, and terminal-native CLI UX prompts. WHEN: \"turn this into a prompt\", \"write a design brief\", \"CLI prompt\", \"terminal-native CLI\", \"polish this prompt\"."
license: MIT
metadata:
  author: ChatGPT
  version: "1.0.0"
---

# Terminal CLI Prompt Writer

## Workflow

1. **Identify the source idea** - Extract the user's goal, constraints, style notes, and target audience.
2. **Choose the output shape** - Produce a polished user prompt, a concise design brief, or a terminal-native CLI UX prompt based on the user's request.
3. **Preserve intent** - Keep the original meaning while improving clarity, specificity, and implementation usefulness.
4. **Make it reusable** - Remove one-off chat context unless it is required for the prompt to work.
5. **Use CLI UX language when relevant** - Describe structured, ANSI-styled terminal output with clear sections, aligned columns, readable spacing, color-coded elements, and optional box-drawing borders.
6. **Return only the finished artifact** - Avoid meta-commentary unless the user asks for alternatives or rationale.

## Output Patterns

Use [examples](references/examples.md) for reusable formats.

## Quality Bar

- Plain language, direct instructions, no vague adjectives without behavior.
- Language-agnostic unless the user names a stack.
- Standard CLI output, not a full-screen TUI, unless requested.
- Mention implementation technology only when the user provided it.
