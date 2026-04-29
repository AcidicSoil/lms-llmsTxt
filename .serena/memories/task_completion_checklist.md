# Task Completion Checklist
- Re-read each file immediately before editing when the conversation is long or the file may have changed.
- After code changes, run the relevant pytest targets at minimum; prefer focused tests first, then broader suite when feasible.
- For Python/package-impacting work, also run a packaging or import smoke check when appropriate.
- Do not report success until verification has been run and failing issues addressed.
- If no type checker or linter is configured, state that explicitly instead of implying they passed.
- Preserve compatibility-sensitive surfaces unless the task requires a contract change: CLI flags, artifact names/layout, fallback generation, graph outputs, MCP contract, session-memory append-only behavior, LM Studio boundary.
