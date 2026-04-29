# Ticket State Audit — 2026-04-29

## Scope

Audit existing incomplete ticket plans for dependency-ready implementation work without changing public behavior.

## Current verification snapshot

- `uv run --extra test pytest -q tests/test_repo_digest.py tests/test_lmstudio.py` reported `13 passed, 1 warning` after the TICKET-130 selected-evidence slice.
- `uv run --extra test pytest -q` reported `73 passed, 1 skipped, 6 warnings` after the TICKET-130 selected-evidence slice.
- The skipped test is the LM Studio/GitHub credential integration path, which depends on local external services and credentials.

## Ticket inventory

| Ticket | State in file | Dependency state | Audit result |
|---|---:|---|---|
| `TICKET-100-repository-analyzer-staged-pipeline.md` | `done: true` | Root ticket | Completed with recorded evidence in the ticket. |
| `TICKET-110-pin-and-audit-dspy-litellm-upgrade-path.md` | `done: true` | Root ticket | Completed with recorded dependency pin/audit evidence in the ticket. |
| `TICKET-130-selective-evidence-planning-for-large-repos.md` | `done: true` | Depends on 100 and 110 | Completed in this slice with bounded selected-content fetching, trace evidence, and passing focused/full tests. |
| `TICKET-150-dspy-planned-llmstxt-synthesis-with-deterministic-rendering.md` | `done: false` | Depends on 100, 110, 130 | Dependency-ready next implementation/audit target. Existing code has partial section-planning support; ticket still needs acceptance review and any remaining implementation. |
| `TICKET-170-benchmark-and-evaluation-loop-for-llmstxt-quality.md` | `done: false` | Depends on 130 and 150 | Not dependency-ready until TICKET-150 is complete. |
| `TICKET-190-evaluate-optional-rlm-exploration-path.md` | `done: false` | Depends on 130, 150, 170 | Not dependency-ready until benchmark/evaluation loop exists. |
| `TICKET-210-review-refactor-compatibility-and-rollout-decision.md` | `done: false` | Depends on all prior tickets | Not dependency-ready until all prior tickets are complete. |

## Evidence inspected

- `.plans/dspy-lms-llmstxt-tickets/*.md`
- `pyproject.toml`
- `docs/dependency-audit.md`
- `src/lms_llmsTxt/analyzer.py`
- `src/lms_llmsTxt/models.py`
- `src/lms_llmsTxt/pipeline.py`
- `src/lms_llmsTxt/repo_digest.py`
- `tests/test_analyzer.py`
- `tests/test_repo_digest.py`
- `tests/test_lmstudio.py`

## Dependency-ready next slice

The next dependency-ready ticket is `TICKET-150-dspy-planned-llmstxt-synthesis-with-deterministic-rendering.md`.

Recommended next pass:

1. Inspect TICKET-150 acceptance criteria.
2. Compare current `PlanLLMsSections`, `LLMsDocument`, and deterministic renderer behavior against the ticket.
3. Implement only missing behavior, if any.
4. Run focused analyzer tests first, then full suite.
5. Mark TICKET-150 done only if fresh evidence supports every acceptance criterion.

Suggested focused verification command:

```bash
uv run --extra test pytest -q tests/test_analyzer.py
```

## Do not do yet

- Do not start TICKET-170, TICKET-190, or TICKET-210 until their dependencies are verified complete.
- Do not change dependency versions unless explicitly executing a dependency-upgrade slice under `AGENTS.md` dependency security posture.
- Do not rely on secrets in chat; keep GitHub token setup local.
