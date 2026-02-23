# Brownfield Documentation Review Checklist

This checklist captures items that should be verified by a human reviewer after the brownfield documentation pass.

Pass scope:
- Whole repo system (Python generator + MCP + HyperGraph UI)
- Supplement mode for `docs/architecture.md`
- Tests excluded by request
- No BMAD config updates performed by request

## Summary

- Generated/updated docs to review:
  - `docs/architecture.md`
  - `docs/standards.md`
  - `docs/patterns.md`
- Priority focus:
  - cross-runtime assumptions (Python + Next.js + LM Studio)
  - interface compatibility claims (CLI flags, HyperGraph route modes, MCP URIs)
  - operational docs accuracy after recent changes

## High Priority (Correctness-Sensitive)

1. Verify CLI flag documentation matches implementation.
- Confirm `--ui` and `--ui-base-url` behavior in `src/lms_llmsTxt/cli.py`.
- Confirm `--ui` correctly requires graph generation in docs and code.

2. Verify HyperGraph API route mode documentation.
- Confirm all supported modes in `hypergraph/app/api/generate/route.ts` are accurately listed.
- Confirm request/response shapes for `load-repo-graph` and `generate-repo-graph`.

3. Verify graph artifact contract claims.
- Confirm `repo.graph.json`, `repo.force.json`, and `graph/nodes/*.md` are still emitted by `src/lms_llmsTxt/graph_builder.py` / pipeline flow.
- Confirm path conventions match docs examples (`artifacts/<owner>/<repo>/graph/...`).

4. Verify MCP graph resource contract references.
- Confirm `repo://{repo_id}/graph/nodes/{node_id}` and `lmstxt://graphs/...` are still exposed in `src/lms_llmsTxt_mcp/server.py`.
- Confirm node-id validation behavior in `src/lms_llmsTxt_mcp/graph_resources.py` remains accurate.

## Medium Priority (Inference / Conventions)

1. Validate standards labeled as "Discovered" vs "Recommended".
- Ensure recommendations do not appear as current enforced policy when they are only conventions.

2. Validate cross-runtime operational assumptions.
- Confirm HyperGraph repo-generation mode prerequisites are accurate for the team’s target setup (Python executable availability, `PYTHONPATH`, LM Studio, GitHub token env).

3. Validate confidence scores.
- Adjust section confidence upward/downward if maintainers have stronger knowledge than repo evidence shows.

4. Confirm anti-pattern/hotspot wording.
- Ensure the frontend lint/typecheck blockers in `hypergraph/components/GraphView.tsx` are still current and not already resolved.

## Low Priority (Documentation Hygiene)

1. Check terminology consistency.
- "HyperGraph" vs "graph visualizer" wording across `README.md`, `docs/architecture.md`, and `hypergraph/README.md`.

2. Check duplicate explanations.
- Reduce overlap between `docs/architecture.md` and `docs/patterns.md` if preferred.

3. Add missing links if helpful.
- Link `docs/standards.md` and `docs/patterns.md` from any internal docs hub sections beyond the current `README.md` Documentation Map.

## Explicitly Not Reviewed in This Pass

1. Test suite architecture and test conventions (`tests/`) (excluded by user request).
2. CI/CD pipelines and deployment infrastructure outside repository-local code/docs.
3. Vendor/generated directories (`node_modules`, `.next`, `artifacts`, `.ck`, caches).

## Sign-Off Checklist

1. `docs/architecture.md` reviewed and accepted
2. `docs/standards.md` reviewed and accepted
3. `docs/patterns.md` reviewed and accepted
4. Any incorrect interface claims corrected
5. Confidence scores and review notes updated if needed
