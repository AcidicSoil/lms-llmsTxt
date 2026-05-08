# Dependency audit and pinning notes

## Scope
This project relies on DSPy through `dspy-ai` and indirectly on LiteLLM. Before adding newer planner, optimizer, or RLM-oriented DSPy work, the dependency path is pinned explicitly so builds do not drift to unreviewed releases.

## Reviewed baseline
Pinned versions are aligned to the repository's previously resolved `uv.lock` set:

- `dspy-ai==3.1.0`
- `litellm==1.80.5`
- `lmstudio==1.5.0`
- `llm-ctx==0.0.1`
- `llms-txt==0.0.4`
- `mcp==1.25.0`
- `pydantic==2.12.4`
- `pydantic-settings==2.12.0`
- `requests==2.32.5`
- `python-dotenv==1.2.1`
- `pytest==9.0.1` for dev/test

## Audit notes
- The repo had an unlocked `pyproject.toml` even though `uv.lock` already resolved a concrete dependency set. That left room for accidental upgrades during environment recreation.
- PyPI shows newer DSPy releases are available after the currently resolved `3.1.0` series, including `3.1.2` and `3.1.3`. Those are intentionally not adopted yet until downstream behavior is reviewed.
- The DSPy project has a documented issue against `dspy==3.1.0` around reasoning-model return shapes changing from `str` to structured output in some cases. That means future DSPy upgrades should be validated against this repository's analyzer assumptions before enabling more DSPy-native planning work.
- LiteLLM disclosed a March 2026 supply-chain incident affecting `litellm==1.82.7` and `litellm==1.82.8`. The project is currently pinned below that range, and LiteLLM's incident write-up lists `1.80.5-stable` as a verified clean release. A newer clean `1.83.0` release also exists, but adopting it should be a deliberate follow-up upgrade rather than an implicit drift.
- Existing GitHub advisories also show LiteLLM has had application-security issues in 2025, reinforcing the need to keep the version explicit and reviewed.

## Upgrade blockers / follow-up work
1. Decide whether to stay on the reviewed `dspy-ai==3.1.0` line for planner refactors or deliberately upgrade to a newer `3.1.x` after compatibility testing.
2. Decide whether to remain on the verified-clean `litellm==1.80.5` baseline or move to `1.83.0` after targeted smoke testing.
3. If either DSPy or LiteLLM is upgraded, rerun the generation smoke path and analyzer/fallback tests before enabling selective evidence planning or optimizer work.
