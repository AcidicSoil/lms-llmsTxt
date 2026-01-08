Parent Ticket:

* Title:

  * Add YAML frontmatter with source URL + metadata to `lmstxt` generated artifacts
* Summary:

  * Add YAML frontmatter provenance metadata (source URL + generator/version + model + single per-run UTC timestamp) to the top of all `lmstxt`-generated text artifacts so they are self-describing for downstream ingestion/indexing (e.g., `llms-txt-registry`).
* Source:

  * Link/ID: Not provided
  * Original ticket excerpt (≤25 words) capturing the overall theme:

    * “`lmstxt <repo-url>` should embed provenance metadata directly into generated artifacts … via YAML frontmatter so artifacts are self-describing”
* Global Constraints:

  * Prepend YAML frontmatter (`--- ... ---`) to generated artifacts.
  * Include `source_url` matching the CLI `<repo-url>` input.
  * Include `generator` (CLI/package name + version).
  * Include `model` used for generation.
  * Include a UTC ISO-8601 `timestamp` generated once per run and reused across artifacts from that run.
  * Implement at the “write boundary” so internal content remains unchanged while on-disk artifacts are prefixed.
* Global Environment:

  * OS: Unknown
  * `lmstxt`/package version: Unknown
  * Model/config details: Unknown
* Global Evidence:

  * Proposed frontmatter example (per ticket):

    * `---`
    * `source_url: <https://github.com/tanstack/router>`
    * `generator: lmstxt v0.1.0`
    * `model: qwen-2.5-7b`
    * `timestamp: 2023-10-27T10:00:00Z`
    * `---`
  * Suggested touch points (per ticket):

    * `src/lmstudiotxt_generator/pipeline.py` (primary)
    * Optional: `src/lmstudiotxt_generator/cli.py`, `schema.py`, `fallback.py`, `models.py`
    * Registry consumers: `src/artifact_ingest/ingest.py`, `src/artifact_ingest/index.py`

Split Plan:

* Coverage Map:

  * “Generated artifacts do not include YAML frontmatter … at the top” → T1
  * “Every generated text artifact (e.g., `llms.txt`, `llms-full`, `llms-ctx`) begins with a YAML frontmatter block” → T2
  * “Frontmatter is added at generation time … single computed timestamp per run” → T1
  * “Include `source_url` matching the CLI `<repo-url>` input” → T1
  * “Include generator identifier (name + version)” → T1
  * “Include `model` used for generation” → T1
  * “Prepend YAML frontmatter (`--- ... ---`) to generated artifacts” → T1
  * “Minimal change likely centralized in `pipeline.py` … passing it into `_write_text(...)`” → T1
  * “Add CLI flag support in `cli.py` if frontmatter toggling is desired” → T3
  * “Extend fallback JSON schema (`schema.py`, `fallback.py`) if metadata should also be present in JSON” → T4
  * “Expose computed metadata in `models.py` if needed by downstream callers” → T4
  * “Downstream (registry) … parse frontmatter during ingest in `src/artifact_ingest/ingest.py` … include metadata in `index.py`” → T5
  * “Consider expanding ingest patterns beyond `**/*-llms*.txt` … capture `llms.txt` / `llms-full.txt`” → T5
  * “Out of Scope: Not provided.” → Info-only
  * “Open Items / Unknowns: Exact list of artifacts emitted …” → T2
  * “Open Items / Unknowns: package name/version source of truth …” → T1
  * “Open Items / Unknowns: Whether frontmatter should be optional …” → T3
  * “Open Items / Unknowns: Whether fallback JSON outputs must also include …” → T4
  * “Risks: downstream tooling may need updates … frontmatter does not break parsing assumptions” → T1
  * “Acceptance Criteria: Running `lmstxt <repo-url>` produces `llms.txt` with YAML frontmatter …” → T1
  * “Priority/Severity: Not provided” → Info-only
  * “Labels (optional): enhancement, cli, metadata, provenance, frontmatter, tooling” → Info-only
  * “Files to Modify for Frontmatter” (repeated placeholder text) → Info-only
* Dependencies:

  * T2 depends on T1 because ensuring *all* emitted artifacts are frontmatter-prefixed relies on the core “write boundary” frontmatter mechanism.
  * T3 depends on T1 because toggling frontmatter requires the underlying frontmatter generation/writing behavior.
  * T4 depends on T1 because JSON metadata (if added) should reuse the same computed per-run metadata.
  * T5 depends on T1 because registry parsing relies on frontmatter existing in produced artifacts.
* Split Tickets:

```ticket T1
T# Title:
- Add per-run YAML frontmatter provenance at the pipeline write boundary
Type:
- enhancement
Target Area:
- `src/lmstudiotxt_generator/pipeline.py` (primary), specifically `run_generation(...)` and `_write_text(...)` (per ticket guidance)
Summary:
- Compute provenance metadata once per `lmstxt <repo-url>` run and prepend it as YAML frontmatter to on-disk text artifacts. The frontmatter must include `source_url`, `generator` (name + version), `model`, and a single per-run UTC ISO-8601 `timestamp` reused across artifacts. Implement at the final write boundary so internal content remains unchanged for downstream steps.
In Scope:
- Build YAML frontmatter string once in `run_generation(...)`.
- Include fields: `source_url`, `generator`, `model`, `timestamp` (UTC ISO-8601).
- Ensure one computed timestamp per run is reused for all artifacts produced in that run.
- Prefix on-disk outputs by passing frontmatter into `_write_text(...)` (or equivalent) so artifact body content remains unchanged aside from the prefix.
Out of Scope:
- CLI flag to toggle frontmatter (see T3).
- Adding metadata into fallback JSON outputs (see T4).
- Registry ingestion/index updates (see T5).
Current Behavior (Actual):
- Generated artifacts do not include YAML frontmatter with `source_url` and related metadata at the top.
Expected Behavior:
- Generated text artifacts written by the pipeline begin with a YAML frontmatter block that includes:
  - `source_url` equal to the CLI `<repo-url>` input
  - `generator` (CLI/package name + version)
  - `model`
  - `timestamp` (UTC ISO-8601), reused across artifacts for the run
Reproduction Steps:
1. Run `lmstxt <repo-url>`.
2. Open the generated `llms.txt` (and other generated artifacts).
3. Confirm a YAML frontmatter block exists at the top and fields are populated correctly.
Requirements / Constraints:
- Prepend YAML frontmatter (`--- ... ---`) to generated artifacts.
- Include `source_url` matching the CLI `<repo-url>` input.
- Include generator identifier (name + version).
- Include `model` used for generation.
- Include a UTC `timestamp` generated once per run and reused across artifacts from that run.
- Approach preference: implement at “write boundary” so internal content remains unchanged.
Evidence:
- Proposed example fields (per ticket):
  - `source_url`, `generator`, `model`, `timestamp`
- Suggested primary touch point (per ticket): `src/lmstudiotxt_generator/pipeline.py`
Open Items / Unknowns:
- Exact package name/version source of truth for `generator` value (e.g., `importlib.metadata` vs module constant) is not provided.
- Exact list of artifacts emitted beyond examples is not provided (may affect coverage; see T2).
Risks / Dependencies:
- If any downstream steps parse artifact content, frontmatter could break parsing assumptions; mitigate by adding only at the final on-disk write boundary.
Acceptance Criteria:
- Running `lmstxt <repo-url>` produces `llms.txt` with a YAML frontmatter block at the top.
- Frontmatter includes `source_url` equal to the CLI `<repo-url>` input.
- Frontmatter includes `generator`, `model`, and a UTC ISO-8601 `timestamp`.
- All artifacts produced in the same run share the same `timestamp` value.
- Artifact body content remains otherwise unchanged aside from the prefixed frontmatter.
Priority & Severity (if inferable from input text):
- Priority: Not provided
- Severity: Not provided
Source:
- “We want the final artifacts to have frontmatter also with the url … `lmstxt <repo-url>`”
- “Minimal change likely centralized in `src/lmstudiotxt_generator/pipeline.py` … pass it into `_write_text(...)`”
- “single computed timestamp per run and reused across artifacts”
```

```ticket T2
T# Title:
- Ensure YAML frontmatter is applied to every emitted text artifact (`llms.txt`, `llms-full`, `llms-ctx`, etc.)
Type:
- enhancement
Target Area:
- `src/lmstudiotxt_generator/pipeline.py` and any other artifact-writing call sites used by `lmstxt`
Summary:
- Identify the complete set of text artifacts produced by `lmstxt` and ensure each one is written through the frontmatter-aware write path so every emitted artifact is prefixed consistently. This ensures provenance metadata is present across `llms.txt`, `llms-full`, `llms-ctx`, and any other artifacts emitted by the tool.
In Scope:
- Determine the exact list of artifacts emitted by `lmstxt` (beyond examples mentioned).
- Verify each artifact is written via the frontmatter-prepending writer introduced in T1.
- Update any artifact writing paths that bypass the shared writer so they also receive the same frontmatter (and same per-run timestamp).
Out of Scope:
- Adding/adjusting registry ingest patterns (see T5).
- Making frontmatter optional via CLI flag (see T3).
Current Behavior (Actual):
- Artifacts currently do not include frontmatter; additionally, the full set of emitted artifacts that must receive it is not specified.
Expected Behavior:
- Every generated text artifact emitted by `lmstxt` begins with the required YAML frontmatter block.
- All artifacts from the same run share the same `timestamp` value (from T1’s per-run metadata).
Reproduction Steps:
1. Run `lmstxt <repo-url>`.
2. Enumerate all generated artifacts produced by the run.
3. Open each artifact and confirm YAML frontmatter is present at the top with consistent fields and matching per-run timestamp.
Requirements / Constraints:
- “Every generated text artifact … begins with a YAML frontmatter block” (per ticket).
- Frontmatter is “consistent across all artifacts produced in the same run.”
Evidence:
- Examples called out in ticket: `llms.txt`, `llms-full`, `llms-ctx`.
Open Items / Unknowns:
- Exact list of artifacts emitted by `lmstxt` that must receive frontmatter is not provided.
Risks / Dependencies:
- Depends on T1 for the core frontmatter write mechanism.
Acceptance Criteria:
- A documented/verified list of `lmstxt` emitted text artifacts exists (from actual output behavior).
- Each emitted text artifact is confirmed to have YAML frontmatter at the top.
- All artifacts produced in the same run share the same `timestamp` value.
Priority & Severity (if inferable from input text):
- Priority: Not provided
- Severity: Not provided
Source:
- “Exact list of artifacts emitted by `lmstxt` that must receive frontmatter (beyond examples mentioned).”
- “Every generated text artifact (e.g., `llms.txt`, `llms-full`, `llms-ctx`) begins with … frontmatter”
```

```ticket T3
T# Title:
- Optional: Add CLI flag to enable/disable YAML frontmatter prefixing
Type:
- enhancement
Target Area:
- `src/lmstudiotxt_generator/cli.py` (and wiring into pipeline)
Summary:
- If frontmatter should be optional, add CLI support to toggle whether YAML frontmatter is prepended to generated artifacts. This provides a user-controlled switch while keeping the default behavior unspecified in the ticket.
In Scope:
- Add a CLI flag in `src/lmstudiotxt_generator/cli.py` to toggle frontmatter behavior (flag name not provided).
- Wire the flag through to the generation pipeline so the write boundary can either prepend frontmatter or not.
Out of Scope:
- Changing registry ingestion behavior (see T5).
- Adding metadata to fallback JSON outputs (see T4).
Current Behavior (Actual):
- No frontmatter exists today; no CLI toggling behavior is defined.
Expected Behavior:
- When frontmatter is enabled, generated artifacts are prefixed with the YAML frontmatter block.
- When frontmatter is disabled, generated artifacts are written without the YAML frontmatter prefix.
Reproduction Steps:
1. Run `lmstxt <repo-url>` with frontmatter enabled (via the new CLI flag behavior).
2. Verify artifacts contain YAML frontmatter.
3. Run `lmstxt <repo-url>` with frontmatter disabled.
4. Verify artifacts do not contain YAML frontmatter.
Requirements / Constraints:
- “Add CLI flag support … if frontmatter toggling is desired” (per ticket).
Evidence:
- Optional/nice-to-have list includes: “Add CLI flag support in `src/lmstudiotxt_generator/cli.py`…”
Open Items / Unknowns:
- Whether frontmatter should be optional via CLI flag or always-on is not provided.
- Exact CLI flag name and default behavior are not provided.
Risks / Dependencies:
- Depends on T1 for the underlying frontmatter generation/write behavior.
Acceptance Criteria:
- A CLI flag exists that controls whether YAML frontmatter is prepended.
- With the flag set to enable, artifacts contain the YAML frontmatter prefix.
- With the flag set to disable, artifacts do not contain the YAML frontmatter prefix.
Priority & Severity (if inferable from input text):
- Priority: Not provided
- Severity: Not provided
Source:
- “Optional/nice-to-have … Add CLI flag support in `src/lmstudiotxt_generator/cli.py` if frontmatter toggling is desired.”
- “Whether frontmatter should be optional via CLI flag or always-on.”
```

```ticket T4
T# Title:
- Optional: Extend fallback JSON schema/output to include provenance metadata (source_url, generator, model, timestamp)
Type:
- enhancement
Target Area:
- `src/lmstudiotxt_generator/schema.py`, `src/lmstudiotxt_generator/fallback.py`, and optionally `src/lmstudiotxt_generator/models.py`
Summary:
- If the project’s fallback JSON outputs (and/or internal models) should carry the same provenance metadata as text artifacts, extend the schema and fallback writer to include `source_url`, `generator`, `model`, and the per-run UTC ISO-8601 `timestamp`. This keeps metadata available even when consuming JSON rather than parsing frontmatter.
In Scope:
- Extend fallback JSON schema in `schema.py` to include provenance metadata fields (if metadata should be present in JSON).
- Update fallback output generation in `fallback.py` to populate these fields.
- Optionally expose computed metadata in `models.py` “if needed by downstream callers” (per ticket).
Out of Scope:
- Text artifact YAML frontmatter behavior (see T1/T2).
- CLI toggle behavior (see T3).
- Registry ingestion/index updates (see T5).
Current Behavior (Actual):
- Fallback JSON metadata behavior is not described; ticket implies metadata is not present today.
Expected Behavior:
- When fallback JSON output is produced, it contains the same provenance metadata fields:
  - `source_url`, `generator`, `model`, `timestamp` (UTC ISO-8601; single per-run value reused)
Reproduction Steps:
1. Run `lmstxt <repo-url>` in a scenario that triggers fallback JSON output (trigger not provided).
2. Inspect produced JSON and confirm provenance metadata fields exist and are populated.
Requirements / Constraints:
- “Extend fallback JSON schema … if metadata should also be present in JSON” (optional per ticket).
Evidence:
- Optional/nice-to-have list includes: `schema.py`, `fallback.py`, `models.py`.
Open Items / Unknowns:
- Whether fallback JSON outputs must also include the same metadata is not provided.
- Exact fallback JSON shape and trigger conditions are not provided.
Risks / Dependencies:
- Depends on T1 for a single source of computed per-run metadata (avoid multiple timestamps per run).
Acceptance Criteria:
- If enabled/implemented, fallback JSON schema includes `source_url`, `generator`, `model`, `timestamp`.
- Produced fallback JSON outputs populate these fields and reuse the per-run timestamp consistently.
Priority & Severity (if inferable from input text):
- Priority: Not provided
- Severity: Not provided
Source:
- “Extend fallback JSON schema (`src/lmstudiotxt_generator/schema.py`, `.../fallback.py`) if metadata should also be present in JSON.”
- “Expose computed metadata in `src/lmstudiotxt_generator/models.py` if needed by downstream callers.”
- “Whether fallback JSON outputs must also include the same metadata.”
```

```ticket T5
T# Title:
- Update `llms-txt-registry` ingestion/indexing to parse YAML frontmatter provenance from `lmstxt` artifacts
Type:
- enhancement
Target Area:
- Downstream repo: `llms-txt-registry` — `src/artifact_ingest/ingest.py` and `src/artifact_ingest/index.py` (and related ingest pattern configuration if applicable)
Summary:
- Update the downstream registry ingestion pipeline to parse YAML frontmatter from ingested `lmstxt` artifacts and store the extracted provenance metadata for indexing/lookup. This supports the stated motivation to avoid reliance on external metadata and directory conventions.
In Scope:
- Parse YAML frontmatter during ingest in `src/artifact_ingest/ingest.py`.
- Include extracted metadata in the index in `src/artifact_ingest/index.py`.
- Consider expanding ingest patterns beyond `**/*-llms*.txt` if the registry should capture `llms.txt` / `llms-full.txt` consistently (as noted in the ticket).
Out of Scope:
- Implementing frontmatter emission in `lmstxt` itself (see T1/T2).
- Adding CLI toggles or fallback JSON metadata in `lmstxt` (see T3/T4).
Current Behavior (Actual):
- Registry ingestion currently relies on external metadata/directory conventions; frontmatter parsing is not described.
Expected Behavior:
- Registry ingest extracts `source_url`, `generator`, `model`, `timestamp` from YAML frontmatter and makes it available for indexing and reverse lookup.
Reproduction Steps:
1. Generate artifacts via `lmstxt <repo-url>` that include YAML frontmatter (requires T1/T2).
2. Ingest artifacts with `llms-txt-registry`.
3. Confirm ingest/index stores and exposes extracted provenance metadata.
Requirements / Constraints:
- Motivation: “needs embedded provenance to avoid reliance on external metadata and directory conventions.”
Evidence:
- Downstream integration opportunity (per ticket):
  - “parse frontmatter during ingest in `src/artifact_ingest/ingest.py` … include metadata in `src/artifact_ingest/index.py`”
  - “Consider expanding ingest patterns beyond `**/*-llms*.txt`…”
Open Items / Unknowns:
- Current `llms-txt-registry` ingest patterns and exact matching rules are not provided.
- Exact expected registry index fields/format for the metadata are not provided.
Risks / Dependencies:
- Depends on T1/T2 because parsing relies on frontmatter being present in produced artifacts.
Acceptance Criteria:
- Registry ingestion successfully parses YAML frontmatter from ingested `lmstxt` artifacts.
- Registry index includes extracted `source_url`, `generator`, `model`, `timestamp` for ingested artifacts.
- Ingest patterns capture intended artifact filenames consistently (as applicable to the registry).
Priority & Severity (if inferable from input text):
- Priority: Not provided
- Severity: Not provided
Source:
- “another project … ingests `lmstxt` outputs and needs embedded provenance”
- “parse frontmatter during ingest in `src/artifact_ingest/ingest.py` … include metadata in `index.py`”
- “Consider expanding ingest patterns beyond `**/*-llms*.txt`”
```
