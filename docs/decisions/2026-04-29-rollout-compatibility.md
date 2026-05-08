# Rollout Compatibility Review — 2026-04-29

## Scope

Review cumulative TICKET-100 through TICKET-190 work against the preserved product surface before final rollout.

## Reviewed surfaces

| Surface | Finding | Evidence |
|---|---|---|
| CLI surface and flags | Preserved. No RLM rollout flag is exposed. Existing graph, UI, output, model, graph-only, and session-memory flags remain present. | `tests/test_rollout_compatibility.py::test_cli_contract_exposes_existing_flags_without_rlm_rollout_flag` |
| Artifact naming and directory structure | Preserved. `GenerationArtifacts` keeps the existing llms.txt, llms-full, ctx, fallback JSON, graph, trace, fallback status, and fallback reason fields. | `tests/test_rollout_compatibility.py::test_generation_artifacts_contract_retains_expected_fields` |
| Graph outputs | Preserved. Prior graph tests verify `repo.graph.json`, `repo.force.json`, and `nodes/moc.md` emission. | `tests/test_graph_builder.py` |
| Fallback path | Preserved and separate from DSPy/RLM scaffolds. Fallback payload and markdown retain the fallback marker and schema-backed JSON payload. | `tests/test_rollout_compatibility.py::test_fallback_payload_and_markdown_contract_remain_separate_from_rlm_scaffold` |
| MCP server contract | Preserved by existing MCP tests. No MCP server rewrite was performed in TICKET-170 or TICKET-190. | `tests/test_llmstxt_mcp_*.py`, full suite |
| Session-memory append-only model | Preserved by existing session memory tests. No rewrite was performed in TICKET-170 or TICKET-190. | `tests/test_session_memory.py`, full suite |
| LM Studio integration boundary | Preserved. TICKET-170 and TICKET-190 added deterministic evaluation scaffolds only; no LM Studio configuration or model-loading path changed. | Full suite and no dependency/config changes in this slice |
| Dependency posture | Preserved. No dependency versions or package-manager settings were changed. | `pyproject.toml` unchanged by this slice; `AGENTS.md` posture applied |

## Evaluation review

TICKET-170 added deterministic benchmark/evaluation helpers for llms.txt quality metrics and graph-based coverage/omission checks.

TICKET-190 added optional deterministic RLM-style exploration evaluation scaffolding with hard depth, file-count, and character budget enforcement. The path remains optional and is not wired into CLI or fallback behavior.

## Rollout decision

Technical compatibility evidence supports proceeding with the refactor as an internal compatible implementation state.

External/product rollout should remain gated until a final human rollout owner and approval venue are identified. No external rollout owner was provided in the ticket state.

Decision: **technical proceed; external rollout gated pending owner approval**.

## Deviations / unknowns

- Final rollout owner: Unknown.
- Final approval venue: Unknown.
- Exact external benchmark repository set: Unknown.
- Exact model-backed RLM integration surface: Unknown and intentionally not adopted.

## Verification evidence

- `uv run --extra test pytest -q tests/test_rollout_compatibility.py --tb=short` reported `4 passed, 12 warnings`.
- `uv run --extra test pytest -q tests/test_rollout_compatibility.py tests/test_rlm_evaluation.py tests/test_evaluation.py tests/test_analyzer.py tests/test_repo_digest.py tests/test_graph_builder.py tests/test_cli_ui.py tests/test_session_memory.py --tb=short` reported `36 passed, 12 warnings`.
- `uv run --extra test pytest -q --tb=short` reported `94 passed, 1 skipped, 18 warnings`.
