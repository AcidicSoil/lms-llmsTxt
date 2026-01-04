# oracle strategist question pack

---

## parsed args

- codebase_name: Unknown
- constraints: None
- non_goals: None
- team_size: Unknown
- deadline: Unknown
- out_dir: oracle-out
- oracle_cmd: oracle
- oracle_flags: --files-report
- extra_files: empty

---

## commands (exactly 20; sorted by ROI desc; ties by lower effort)

```bash
# 01 — ROI=2.13 impact=0.8 confidence=0.8 effort=0.3 horizon=Immediate category=permissions reference=src/llmstxt_mcp/security.py:validate_output_dir
oracle \
  --files-report \
  --write-output "oracle-out/01-permissions-validate-output-dir.md" \
  -p "Strategist question #01
Reference: src/llmstxt_mcp/security.py:validate_output_dir
Category: permissions
Horizon: Immediate
ROI: 2.13 (impact=0.8, confidence=0.8, effort=0.3)
Question: Does validate_output_dir fully prevent path traversal or symlink escapes when output_dir comes from MCP tool inputs?
Rationale: The MCP server writes files on behalf of users and must enforce a strict filesystem boundary.
Smallest experiment today: Run `ck --regex 'validate_output_dir' -n src/llmstxt_mcp/security.py`.
Constraints: None
Non-goals: None

Answer format:
1) Direct answer (1–4 bullets, evidence-cited)
2) Risks/unknowns (bullets)
3) Next smallest concrete experiment (1 action) — may differ from the suggested one if you justify it
4) If evidence is insufficient, name the exact missing file/path pattern(s) to attach next." \
  -f "src/llmstxt_mcp/security.py" \
  -f "src/llmstxt_mcp/config.py"

# 02 — ROI=2.10 impact=0.6 confidence=0.7 effort=0.2 horizon=Immediate category=observability reference=src/llmstxt_mcp/server.py:logging.basicConfig
oracle \
  --files-report \
  --write-output "oracle-out/02-observability-server-logging.md" \
  -p "Strategist question #02
Reference: src/llmstxt_mcp/server.py:logging.basicConfig
Category: observability
Horizon: Immediate
ROI: 2.10 (impact=0.6, confidence=0.7, effort=0.2)
Question: Are logging levels and stderr routing sufficient to avoid JSON-RPC interference while still capturing run_id-level diagnostics?
Rationale: The MCP server must not write to stdout and still needs actionable error traces.
Smallest experiment today: Run `ck --regex 'basicConfig|logger' -n src/llmstxt_mcp/server.py`.
Constraints: None
Non-goals: None

Answer format:
1) Direct answer (1–4 bullets, evidence-cited)
2) Risks/unknowns (bullets)
3) Next smallest concrete experiment (1 action) — may differ from the suggested one if you justify it
4) If evidence is insufficient, name the exact missing file/path pattern(s) to attach next." \
  -f "src/llmstxt_mcp/server.py"

# 03 — ROI=2.10 impact=0.9 confidence=0.7 effort=0.3 horizon=Immediate category=failure modes reference=src/lmstudiotxt_generator/pipeline.py:run_generation
oracle \
  --files-report \
  --write-output "oracle-out/03-failure-modes-run-generation.md" \
  -p "Strategist question #03
Reference: src/lmstudiotxt_generator/pipeline.py:run_generation
Category: failure modes
Horizon: Immediate
ROI: 2.10 (impact=0.9, confidence=0.7, effort=0.3)
Question: Does run_generation cover the right exception classes and guarantee a sane fallback output without masking actionable errors?
Rationale: The generator promises llms.txt output even when LM calls fail.
Smallest experiment today: Run `ck --regex 'LiteLLM|LMStudioConnectivityError|fallback' -n src/lmstudiotxt_generator/pipeline.py`.
Constraints: None
Non-goals: None

Answer format:
1) Direct answer (1–4 bullets, evidence-cited)
2) Risks/unknowns (bullets)
3) Next smallest concrete experiment (1 action) — may differ from the suggested one if you justify it
4) If evidence is insufficient, name the exact missing file/path pattern(s) to attach next." \
  -f "src/lmstudiotxt_generator/pipeline.py"

# 04 — ROI=1.80 impact=0.6 confidence=0.6 effort=0.2 horizon=Immediate category=feature flags reference=src/lmstudiotxt_generator/config.py:AppConfig
oracle \
  --files-report \
  --write-output "oracle-out/04-feature-flags-appconfig.md" \
  -p "Strategist question #04
Reference: src/lmstudiotxt_generator/config.py:AppConfig
Category: feature flags
Horizon: Immediate
ROI: 1.80 (impact=0.6, confidence=0.6, effort=0.2)
Question: Are CLI flags and env overrides consistent with AppConfig defaults (ENABLE_CTX, LINK_STYLE, LMSTUDIO_*), or are there gaps that should be documented?
Rationale: Configuration mismatches create hard-to-debug behavior for users.
Smallest experiment today: Run `ck --regex 'ENABLE_CTX|LMSTUDIO_AUTO_UNLOAD|LMSTUDIO_STREAMING|link_style' -n src/lmstudiotxt_generator/config.py`.
Constraints: None
Non-goals: None

Answer format:
1) Direct answer (1–4 bullets, evidence-cited)
2) Risks/unknowns (bullets)
3) Next smallest concrete experiment (1 action) — may differ from the suggested one if you justify it
4) If evidence is insufficient, name the exact missing file/path pattern(s) to attach next." \
  -f "src/lmstudiotxt_generator/config.py"

# 05 — ROI=1.60 impact=0.8 confidence=0.6 effort=0.3 horizon=Immediate category=failure modes reference=src/lmstudiotxt_generator/lmstudio.py:_fetch_models
oracle \
  --files-report \
  --write-output "oracle-out/05-failure-modes-fetch-models.md" \
  -p "Strategist question #05
Reference: src/lmstudiotxt_generator/lmstudio.py:_fetch_models
Category: failure modes
Horizon: Immediate
ROI: 1.60 (impact=0.8, confidence=0.6, effort=0.3)
Question: Does LM Studio endpoint probing handle API variants robustly and provide actionable errors when no endpoint succeeds?
Rationale: Model discovery is a hard dependency for generation to proceed.
Smallest experiment today: Run `ck --regex '_MODEL_ENDPOINTS|_fetch_models' -n src/lmstudiotxt_generator/lmstudio.py`.
Constraints: None
Non-goals: None

Answer format:
1) Direct answer (1–4 bullets, evidence-cited)
2) Risks/unknowns (bullets)
3) Next smallest concrete experiment (1 action) — may differ from the suggested one if you justify it
4) If evidence is insufficient, name the exact missing file/path pattern(s) to attach next." \
  -f "src/lmstudiotxt_generator/lmstudio.py"

# 06 — ROI=1.50 impact=0.5 confidence=0.6 effort=0.2 horizon=Immediate category=UX flows reference=src/lmstudiotxt_generator/cli.py:main
oracle \
  --files-report \
  --write-output "oracle-out/06-ux-flows-cli-main.md" \
  -p "Strategist question #06
Reference: src/lmstudiotxt_generator/cli.py:main
Category: UX flows
Horizon: Immediate
ROI: 1.50 (impact=0.5, confidence=0.6, effort=0.2)
Question: Are CLI error handling and exit codes suitable for automation, and does the summary output surface fallback usage clearly?
Rationale: The CLI is the primary user-facing workflow for the generator.
Smallest experiment today: Run `ck --regex 'parser.error|summary|print' -n src/lmstudiotxt_generator/cli.py`.
Constraints: None
Non-goals: None

Answer format:
1) Direct answer (1–4 bullets, evidence-cited)
2) Risks/unknowns (bullets)
3) Next smallest concrete experiment (1 action) — may differ from the suggested one if you justify it
4) If evidence is insufficient, name the exact missing file/path pattern(s) to attach next." \
  -f "src/lmstudiotxt_generator/cli.py"

# 07 — ROI=1.23 impact=0.7 confidence=0.7 effort=0.4 horizon=Immediate category=caching/state reference=src/llmstxt_mcp/runs.py:RunStore
oracle \
  --files-report \
  --write-output "oracle-out/07-caching-state-runstore.md" \
  -p "Strategist question #07
Reference: src/llmstxt_mcp/runs.py:RunStore
Category: caching/state
Horizon: Immediate
ROI: 1.23 (impact=0.7, confidence=0.7, effort=0.4)
Question: Is the in-memory RunStore durable enough for expected usage, or do we risk losing run history or exceeding max_runs under load?
Rationale: RunStore is the sole state layer for MCP run tracking.
Smallest experiment today: Run `ck --regex 'class RunStore|_runs' -n src/llmstxt_mcp/runs.py`.
Constraints: None
Non-goals: None

Answer format:
1) Direct answer (1–4 bullets, evidence-cited)
2) Risks/unknowns (bullets)
3) Next smallest concrete experiment (1 action) — may differ from the suggested one if you justify it
4) If evidence is insufficient, name the exact missing file/path pattern(s) to attach next." \
  -f "src/llmstxt_mcp/runs.py"

# 08 — ROI=1.17 impact=0.7 confidence=0.5 effort=0.3 horizon=Immediate category=invariants reference=src/lmstudiotxt_generator/github.py:owner_repo_from_url
oracle \
  --files-report \
  --write-output "oracle-out/08-invariants-owner-repo-from-url.md" \
  -p "Strategist question #08
Reference: src/lmstudiotxt_generator/github.py:owner_repo_from_url
Category: invariants
Horizon: Immediate
ROI: 1.17 (impact=0.7, confidence=0.5, effort=0.3)
Question: Are the accepted GitHub URL patterns comprehensive and normalized enough to avoid mis-parsing edge cases?
Rationale: URL parsing drives every downstream GitHub API request.
Smallest experiment today: Run `ck --regex 'owner_repo_from_url|_GITHUB_URL' -n src/lmstudiotxt_generator/github.py`.
Constraints: None
Non-goals: None

Answer format:
1) Direct answer (1–4 bullets, evidence-cited)
2) Risks/unknowns (bullets)
3) Next smallest concrete experiment (1 action) — may differ from the suggested one if you justify it
4) If evidence is insufficient, name the exact missing file/path pattern(s) to attach next." \
  -f "src/lmstudiotxt_generator/github.py"

# 09 — ROI=1.05 impact=0.7 confidence=0.6 effort=0.4 horizon=Immediate category=failure modes reference=src/lmstudiotxt_generator/full_builder.py:build_llms_full_from_repo
oracle \
  --files-report \
  --write-output "oracle-out/09-failure-modes-build-llms-full.md" \
  -p "Strategist question #09
Reference: src/lmstudiotxt_generator/full_builder.py:build_llms_full_from_repo
Category: failure modes
Horizon: Immediate
ROI: 1.05 (impact=0.7, confidence=0.6, effort=0.4)
Question: Are HTTP errors and size truncation handled in llms-full generation in a way that preserves useful diagnostics for users?
Rationale: llms-full output should remain trustworthy even when upstream fetches fail.
Smallest experiment today: Run `ck --regex 'build_llms_full_from_repo|_format_http_error' -n src/lmstudiotxt_generator/full_builder.py`.
Constraints: None
Non-goals: None

Answer format:
1) Direct answer (1–4 bullets, evidence-cited)
2) Risks/unknowns (bullets)
3) Next smallest concrete experiment (1 action) — may differ from the suggested one if you justify it
4) If evidence is insufficient, name the exact missing file/path pattern(s) to attach next." \
  -f "src/lmstudiotxt_generator/full_builder.py"

# 10 — ROI=1.00 impact=0.5 confidence=0.6 effort=0.3 horizon=Immediate category=background jobs reference=src/llmstxt_mcp/runs.py:start_cleanup_worker
oracle \
  --files-report \
  --write-output "oracle-out/10-background-jobs-cleanup-worker.md" \
  -p "Strategist question #10
Reference: src/llmstxt_mcp/runs.py:start_cleanup_worker
Category: background jobs
Horizon: Immediate
ROI: 1.00 (impact=0.5, confidence=0.6, effort=0.3)
Question: Does the cleanup worker prune runs safely and avoid thread leaks or unbounded log spam?
Rationale: Background cleanup keeps state bounded but can destabilize the server if misconfigured.
Smallest experiment today: Run `ck --regex 'start_cleanup_worker|prune_expired' -n src/llmstxt_mcp/runs.py`.
Constraints: None
Non-goals: None

Answer format:
1) Direct answer (1–4 bullets, evidence-cited)
2) Risks/unknowns (bullets)
3) Next smallest concrete experiment (1 action) — may differ from the suggested one if you justify it
4) If evidence is insufficient, name the exact missing file/path pattern(s) to attach next." \
  -f "src/llmstxt_mcp/runs.py"

# 11 — ROI=1.00 impact=0.6 confidence=0.5 effort=0.3 horizon=Immediate category=contracts/interfaces reference=src/llmstxt_mcp/models.py:RunRecord
oracle \
  --files-report \
  --write-output "oracle-out/11-contracts-runrecord.md" \
  -p "Strategist question #11
Reference: src/llmstxt_mcp/models.py:RunRecord
Category: contracts/interfaces
Horizon: Immediate
ROI: 1.00 (impact=0.6, confidence=0.5, effort=0.3)
Question: Do RunRecord and ArtifactRef provide enough metadata for clients to verify artifact integrity and status across tool calls?
Rationale: MCP clients rely on these models as a stable interface contract.
Smallest experiment today: Run `ck --regex 'class RunRecord|ArtifactRef' -n src/llmstxt_mcp/models.py`.
Constraints: None
Non-goals: None

Answer format:
1) Direct answer (1–4 bullets, evidence-cited)
2) Risks/unknowns (bullets)
3) Next smallest concrete experiment (1 action) — may differ from the suggested one if you justify it
4) If evidence is insufficient, name the exact missing file/path pattern(s) to attach next." \
  -f "src/llmstxt_mcp/models.py"

# 12 — ROI=0.75 impact=0.6 confidence=0.5 effort=0.4 horizon=Immediate category=caching/state reference=src/llmstxt_mcp/generator.py:_lock
oracle \
  --files-report \
  --write-output "oracle-out/12-caching-state-global-lock.md" \
  -p "Strategist question #12
Reference: src/llmstxt_mcp/generator.py:_lock
Category: caching/state
Horizon: Immediate
ROI: 0.75 (impact=0.6, confidence=0.5, effort=0.4)
Question: Is the global generation lock overly restrictive, preventing safe parallel runs for different repositories?
Rationale: Lock scope directly impacts throughput for MCP clients.
Smallest experiment today: Run `ck --regex '_lock|safe_generate_llms_txt' -n src/llmstxt_mcp/generator.py`.
Constraints: None
Non-goals: None

Answer format:
1) Direct answer (1–4 bullets, evidence-cited)
2) Risks/unknowns (bullets)
3) Next smallest concrete experiment (1 action) — may differ from the suggested one if you justify it
4) If evidence is insufficient, name the exact missing file/path pattern(s) to attach next." \
  -f "src/llmstxt_mcp/generator.py"

# 13 — ROI=0.70 impact=0.7 confidence=0.5 effort=0.5 horizon=Strategic category=contracts/interfaces reference=src/lmstudiotxt_generator/schema.py:LLMS_JSON_SCHEMA
oracle \
  --files-report \
  --write-output "oracle-out/13-contracts-llms-json-schema.md" \
  -p "Strategist question #13
Reference: src/lmstudiotxt_generator/schema.py:LLMS_JSON_SCHEMA
Category: contracts/interfaces
Horizon: Strategic
ROI: 0.70 (impact=0.7, confidence=0.5, effort=0.5)
Question: Should LLMS_JSON_SCHEMA include explicit versioning or extension points to support future tooling evolution?
Rationale: A stable schema contract reduces downstream breakage as features grow.
Smallest experiment today: Run `ck --regex 'LLMS_JSON_SCHEMA' -n src/lmstudiotxt_generator/schema.py`.
Constraints: None
Non-goals: None

Answer format:
1) Direct answer (1–4 bullets, evidence-cited)
2) Risks/unknowns (bullets)
3) Next smallest concrete experiment (1 action) — may differ from the suggested one if you justify it
4) If evidence is insufficient, name the exact missing file/path pattern(s) to attach next." \
  -f "src/lmstudiotxt_generator/schema.py"

# 14 — ROI=0.60 impact=0.6 confidence=0.4 effort=0.4 horizon=Strategic category=permissions reference=src/llmstxt_mcp/config.py:LLMSTXT_MCP_ALLOWED_ROOT
oracle \
  --files-report \
  --write-output "oracle-out/14-permissions-allowed-root.md" \
  -p "Strategist question #14
Reference: src/llmstxt_mcp/config.py:LLMSTXT_MCP_ALLOWED_ROOT
Category: permissions
Horizon: Strategic
ROI: 0.60 (impact=0.6, confidence=0.4, effort=0.4)
Question: Is a single allowed root sufficient for future multi-tenant deployments, or should we support per-request roots?
Rationale: Filesystem boundaries are a key security control for shared deployments.
Smallest experiment today: Run `ck --regex 'LLMSTXT_MCP_ALLOWED_ROOT' -n src/llmstxt_mcp/config.py`.
Constraints: None
Non-goals: None

Answer format:
1) Direct answer (1–4 bullets, evidence-cited)
2) Risks/unknowns (bullets)
3) Next smallest concrete experiment (1 action) — may differ from the suggested one if you justify it
4) If evidence is insufficient, name the exact missing file/path pattern(s) to attach next." \
  -f "src/llmstxt_mcp/config.py"

# 15 — ROI=0.60 impact=0.6 confidence=0.5 effort=0.5 horizon=Strategic category=background jobs reference=src/llmstxt_mcp/server.py:_spawn_background
oracle \
  --files-report \
  --write-output "oracle-out/15-background-jobs-spawn-background.md" \
  -p "Strategist question #15
Reference: src/llmstxt_mcp/server.py:_spawn_background
Category: background jobs
Horizon: Strategic
ROI: 0.60 (impact=0.6, confidence=0.5, effort=0.5)
Question: Should background task execution include cancellation/timeout or job state tracking beyond RunStore status?
Rationale: Long-running or stuck background jobs can degrade server reliability.
Smallest experiment today: Run `ck --regex '_spawn_background' -n src/llmstxt_mcp/server.py`.
Constraints: None
Non-goals: None

Answer format:
1) Direct answer (1–4 bullets, evidence-cited)
2) Risks/unknowns (bullets)
3) Next smallest concrete experiment (1 action) — may differ from the suggested one if you justify it
4) If evidence is insufficient, name the exact missing file/path pattern(s) to attach next." \
  -f "src/llmstxt_mcp/server.py"

# 16 — ROI=0.58 impact=0.7 confidence=0.5 effort=0.6 horizon=Strategic category=caching/state reference=src/lmstudiotxt_generator/config.py:lm_auto_unload
oracle \
  --files-report \
  --write-output "oracle-out/16-caching-state-lm-auto-unload.md" \
  -p "Strategist question #16
Reference: src/lmstudiotxt_generator/config.py:lm_auto_unload
Category: caching/state
Horizon: Strategic
ROI: 0.58 (impact=0.7, confidence=0.5, effort=0.6)
Question: Should we introduce a persistent LM cache or model reuse strategy, and how would it interact with lm_auto_unload?
Rationale: Model lifecycle choices directly affect performance and resource use.
Smallest experiment today: Run `ck --regex 'lm_auto_unload|cache_lm' -n src/lmstudiotxt_generator/config.py`.
Constraints: None
Non-goals: None

Answer format:
1) Direct answer (1–4 bullets, evidence-cited)
2) Risks/unknowns (bullets)
3) Next smallest concrete experiment (1 action) — may differ from the suggested one if you justify it
4) If evidence is insufficient, name the exact missing file/path pattern(s) to attach next." \
  -f "src/lmstudiotxt_generator/config.py"

# 17 — ROI=0.50 impact=0.5 confidence=0.4 effort=0.4 horizon=Strategic category=feature flags reference=src/lmstudiotxt_generator/config.py:_env_flag
oracle \
  --files-report \
  --write-output "oracle-out/17-feature-flags-env-flag.md" \
  -p "Strategist question #17
Reference: src/lmstudiotxt_generator/config.py:_env_flag
Category: feature flags
Horizon: Strategic
ROI: 0.50 (impact=0.5, confidence=0.4, effort=0.4)
Question: Do we need stricter validation or telemetry for env flags to avoid silent misconfiguration?
Rationale: Silent env parsing errors can lead to hard-to-diagnose behavior.
Smallest experiment today: Run `ck --regex '_env_flag' -n src/lmstudiotxt_generator/config.py`.
Constraints: None
Non-goals: None

Answer format:
1) Direct answer (1–4 bullets, evidence-cited)
2) Risks/unknowns (bullets)
3) Next smallest concrete experiment (1 action) — may differ from the suggested one if you justify it
4) If evidence is insufficient, name the exact missing file/path pattern(s) to attach next." \
  -f "src/lmstudiotxt_generator/config.py"

# 18 — ROI=0.48 impact=0.6 confidence=0.4 effort=0.5 horizon=Strategic category=observability reference=src/lmstudiotxt_generator/pipeline.py:logger
oracle \
  --files-report \
  --write-output "oracle-out/18-observability-pipeline-logging.md" \
  -p "Strategist question #18
Reference: src/lmstudiotxt_generator/pipeline.py:logger
Category: observability
Horizon: Strategic
ROI: 0.48 (impact=0.6, confidence=0.4, effort=0.5)
Question: Do we need structured logging or metrics for generation duration, fallback rate, and GitHub fetch failures?
Rationale: Observability gaps slow diagnosis for long-running jobs.
Smallest experiment today: Run `ck --regex 'logger\.|logging' -n src/lmstudiotxt_generator/pipeline.py`.
Constraints: None
Non-goals: None

Answer format:
1) Direct answer (1–4 bullets, evidence-cited)
2) Risks/unknowns (bullets)
3) Next smallest concrete experiment (1 action) — may differ from the suggested one if you justify it
4) If evidence is insufficient, name the exact missing file/path pattern(s) to attach next." \
  -f "src/lmstudiotxt_generator/pipeline.py"

# 19 — ROI=0.40 impact=0.5 confidence=0.4 effort=0.5 horizon=Strategic category=UX flows reference=src/llmstxt_mcp/artifacts.py:read_resource_text
oracle \
  --files-report \
  --write-output "oracle-out/19-ux-flows-artifact-reading.md" \
  -p "Strategist question #19
Reference: src/llmstxt_mcp/artifacts.py:read_resource_text
Category: UX flows
Horizon: Strategic
ROI: 0.40 (impact=0.5, confidence=0.4, effort=0.5)
Question: Should MCP artifact reading include pagination metadata or chunk cursors to improve client UX for large outputs?
Rationale: Large artifacts are a common UX bottleneck for downstream clients.
Smallest experiment today: Run `ck --regex 'read_resource_text|read_artifact_chunk' -n src/llmstxt_mcp/artifacts.py`.
Constraints: None
Non-goals: None

Answer format:
1) Direct answer (1–4 bullets, evidence-cited)
2) Risks/unknowns (bullets)
3) Next smallest concrete experiment (1 action) — may differ from the suggested one if you justify it
4) If evidence is insufficient, name the exact missing file/path pattern(s) to attach next." \
  -f "src/llmstxt_mcp/artifacts.py"

# 20 — ROI=0.30 impact=0.6 confidence=0.3 effort=0.6 horizon=Strategic category=migrations reference=Unknown
oracle \
  --files-report \
  --write-output "oracle-out/20-migrations-unknown.md" \
  -p "Strategist question #20
Reference: Unknown
Category: migrations
Horizon: Strategic
ROI: 0.30 (impact=0.6, confidence=0.3, effort=0.6)
Question: With no migration tooling found (no **/migrations/**), what migration/versioning plan should be defined for future artifact schema or run-storage changes?
Rationale: Schema evolution without a migration plan can break clients and historic artifacts.
Smallest experiment today: Run `fd -p 'migrations' .`.
Constraints: None
Non-goals: None

Answer format:
1) Direct answer (1–4 bullets, evidence-cited)
2) Risks/unknowns (bullets)
3) Next smallest concrete experiment (1 action) — may differ from the suggested one if you justify it
4) If evidence is insufficient, name the exact missing file/path pattern(s) to attach next." \
  -f "README.md" \
  -f "pyproject.toml" \
  -f "src/lmstudiotxt_generator/cli.py"
```

---

## coverage check (must be satisfied)

*   contracts/interfaces: OK

*   invariants: OK

*   caching/state: OK

*   background jobs: OK

*   observability: OK

*   permissions: OK

*   migrations: Missing (no **/migrations/** or migration tooling found)

*   UX flows: OK

*   failure modes: OK

*   feature flags: OK
