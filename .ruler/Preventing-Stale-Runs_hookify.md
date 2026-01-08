# Agent Guardrails (Anti-Stall Shell Policy)

## Non-interactive shell constraint (required)

When using any shell/tool execution:

- Only run **non-interactive, self-terminating** commands.
- Never run commands that open editors/REPLs/pagers or wait for stdin (e.g., `vim`, `nano`, `less`, `man`, bare `python`, bare `node`, bare `cat`).
- Never include placeholders like `[current working directory ...]`, `<PATH_HERE>`, `TODO`, or similar in the command. Resolve real paths first.
- For any command that can take noticeable time (tests, builds, servers, migrations), **wrap with a timeout** so it cannot hang:
  - Linux/WSL: `timeout -k 5s 10m <cmd...>`
  - macOS (coreutils): `gtimeout -k 5s 10m <cmd...>`
- For “unknown CLI behavior”, probe using `--help` / `--version` with a short timeout first.

These constraints are enforced by Gemini CLI hooks in `.gemini/settings.json`.

---

# Gemini CLI Project Instructions (Anti-Stale Runs)

## Hard constraint for Shell tool usage

Any `run_shell_command` invocation MUST be:

1) Fully specified (no placeholders like `[current working directory ...]`),
2) Non-interactive (no editors/REPLs/pagers; no waiting on stdin), and
3) Bounded by an explicit timeout for anything that might run longer than a moment.

### Safe templates

**Targeted test run**
- Linux/WSL:
  - `timeout -k 5s 10m pytest -q tests/test_llmstxt_mcp_server.py`
- macOS (coreutils):
  - `gtimeout -k 5s 10m pytest -q tests/test_llmstxt_mcp_server.py`

**CLI discovery**
- `timeout -k 5s 30s llmstxt-mcp --help`

### Disallowed examples (will be blocked)

- `pytest ... && llmstxt-mcp [current working directory ...]`
- `vim file.txt`
- `python` (opens REPL)
- `cat` (waits on stdin)
- `tail -f logfile`

If blocked, revise the command to be non-interactive and/or add an explicit timeout wrapper.
