Direct answer (1–4 bullets, evidence-cited)

Adopt explicit, embedded versioning for every persisted contract (artifacts + run metadata): add schema_version (and generator_version) to JSON artifacts, and add a short header comment to text artifacts (llms.txt, llms-full.txt, llms-ctx.txt) so historic files remain self-describing even when paths are deterministic. This fits the project’s current “artifacts written to artifacts/<owner>/<repo>/” file-centric design. (README.md “Generated artifacts”, “Run ID vs Deterministic Paths”; pyproject.toml shows packaged CLI/server entrypoints you can align to generator_version.)

Define compatibility rules + deprecation policy now: “minor = additive/backward-compatible; major = breaking.” For breaking changes, either (a) write both versions in parallel (preferred for stability) or (b) bump major and provide an upgrader on read. This avoids breaking MCP clients that read prior runs via llmstxt://runs/{run_id}/{artifact_name}. (README.md “Resources” and run_id-based access; README.md notes chunked access/read tooling exists.)

Plan migrations only when persistence is introduced; until then, use ‘lazy upgrades’: today’s run history is described as “recent generation history” and file artifacts are the durable outputs; without a DB layer, formal migrations are mostly about artifact format evolution. Implement upgrade_vN_to_vN+1 functions and apply them when reading older artifacts (server-side), while always writing the latest format. (README.md “llmstxt_list_runs”, “llmstxt_read_artifact”.)

Document a “schema registry” in-repo: a /schemas/ directory (or src/.../schemas/) that pins JSON Schema files per version (e.g., llms.schema.v1.json, llms.schema.v2.json), referenced by $schema/schema_uri and tests. This aligns with the existing mention of LLMS_JSON_SCHEMA for fallback JSON output. (README.md “*-llms.json … following LLMS_JSON_SCHEMA”.)

Risks/unknowns (bullets)

Unknown current artifact on-disk structure beyond README: if there’s already an implicit version (timestamps via --stamp, naming conventions, or headers), adding headers could break strict downstream parsers that assume “pure markdown.” (README.md mentions --stamp comment appends; cli.py shows --stamp support.)

Unknown MCP client expectations: clients may treat artifact_name as stable; introducing new artifact filenames for breaking changes could require capability negotiation or aliasing.

Run storage evolution path is underspecified: if you later add a persistent RunStore (SQLite/JSON index), the migration approach depends on whether you need transactional guarantees and multi-process safety.

Test coverage for backward reads: without snapshot fixtures of older artifacts, “upgrade-on-read” is easy to regress.

Next smallest concrete experiment (1 action)

Add no-op version plumbing end-to-end: introduce schema_version = 1 + generator_version fields into the fallback JSON payload and add a single header line to each text artifact (reusing the existing “stamp comment” mechanism), plus one unit test that asserts these appear in outputs and that readers ignore/strip them safely. This creates the contract surface for future upgrades without changing semantics.

If evidence is insufficient, name the exact missing file/path pattern(s) to attach next.

src/lmstudiotxt_generator/*writer*.py (or wherever text/JSON artifacts are serialized)

src/lmstudiotxt_generator/schema.py (full file; you referenced LLMS_JSON_SCHEMA elsewhere)

src/llmstxt_mcp/models.py and src/llmstxt_mcp/runs.py (full files; to define run-record schema versioning + any persistence hooks)

src/llmstxt_mcp/artifacts.py (resource read path; to implement “upgrade-on-read” and/or content negotiation)
