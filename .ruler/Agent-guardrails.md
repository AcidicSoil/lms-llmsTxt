<!-- path: GEMINI.md -->

# Agent guardrails: shell + tests

## Shell usage must be deterministic and non-interactive

- Only run `run_shell_command` when the command is fully specified and guaranteed to terminate.
- Never run commands that wait for input (prompts/TUIs/editors) or require “payloads” you have not provided.
- Do not chain commands with `&&`, `||`, or `;`. Run exactly one command per tool call.
- Do not background processes with `&` unless explicitly requested by the user.
- If you are unsure a command will finish quickly, wrap it with a time bound (e.g., `timeout 60s ...`) or choose a smaller/targeted check.

## Testing strategy (avoid stale runs)

- Prefer the smallest, targeted test that validates the change (single test file, single test, or narrowed selection).
- If a test requires external dependencies, network, or runtime services:
  - run a fast smoke check first (import/compile/lint)
  - then run the targeted integration test with explicit time bounds
  - if prerequisites are missing, do not run the test—surface the missing prerequisite instead.
