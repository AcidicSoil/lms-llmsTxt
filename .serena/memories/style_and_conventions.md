# Style and Conventions
- Language mix: mostly Python, plus TypeScript/Vue in `hypergraph/`.
- Python style: type hints are used heavily (`str | None`, dataclasses, typed locals), imports are grouped simply, functions are small-to-medium sized with pragmatic docstrings on public dataclasses/classes and occasional helper docstrings.
- Naming: `snake_case` for functions/variables, `PascalCase` for dataclasses/classes, uppercase constants, explicit module-level `logger` patterns.
- Data modeling: lightweight dataclasses in `models.py`/`repo_digest.py`; optional behavior guarded with `try/except ImportError` for soft dependencies.
- Testing style: pytest, monkeypatch-heavy unit tests, straightforward assertions, minimal fixture indirection.
- Compatibility expectation: preserve CLI surface, artifact names/paths, fallback behavior, graph emission, and MCP contracts unless a task explicitly changes them.
- Refactor guidance inferred from repo/tests: prefer deterministic local formatting and keep LM/DSPy behavior behind narrow boundaries; add defensive fallbacks instead of removing compatibility shims abruptly.
