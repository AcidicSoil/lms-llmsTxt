Parent Ticket:

* Title:

  * Clarify lmstxt MCP tool usage (agent guidance) and align MCP “instructions/prompts/resources” delivery
* Summary:

  * Expand `lmstxt-usage.md` so agents correctly call lmstxt MCP tools (required inputs, workflows, failure modes), and implement the standard MCP surfaces for guidance: server `initialize` instructions, tool schemas/annotations, prompts, and resources.
* Source:

  * Link/ID (if present) or “Not provided”
  * Original ticket excerpt (≤25 words) capturing the overall theme

    * “build on the `lmstxt-usage.md` so that it is clear on how to use the lmstxt mcp tools…”
* Global Constraints:

  * `repo_url` must be a repository URL (owner/repo), not an org-only URL.
  * `output_dir` is server-side and must be within `LLMSTXT_MCP_ALLOWED_ROOT`.
  * Prefer `run_id` for reading artifacts after generation.
  * `artifact_name` must be one of: `llms.txt`, `llms-full.txt`, `llms-ctx.txt`, `llms.json`.
* Global Environment:

  * MCP server runs on the machine that writes/reads the artifacts directory.
  * LM Studio must be reachable from the server; uses `LMSTUDIO_BASE_URL` (example shown `http://localhost:1234/v1`).
* Global Evidence:

  * Documented failure modes and correct responses:

    * “Unrecognized GitHub URL”
    * “Output directory not allowed”
    * “LM Studio unavailable” / connection errors
    * “Artifact not found”

Split Plan:

* Coverage Map:

  * “build on the `lmstxt-usage.md` … clear on how to use the lmstxt mcp tools and what input are required …” → T1
  * “Artifacts you can read … `llms.txt`, `llms-full.txt`, `llms-ctx.txt`, `llms.json`” → T1
  * “`repo_url` must be a repository URL … org-only URLs are rejected” → T1
  * “`output_dir` is a server-side path … inside … `LLMSTXT_MCP_ALLOWED_ROOT`” → T1
  * “`run_id` vs `repo_url` … Best practice: prefer `run_id` …” → T1
  * “Artifact file naming … `<output_dir>/<owner>/<repo>/<repo>-<artifact_name>`” → T1
  * “Quick workflows (copy/paste recipes) … Read existing / Generate then read / Generate full or ctx” → T1
  * “Tool reference … inputs required … outputs …” → T3
  * “Common failures (and the correct agent response)” → T1
  * “Advanced: reading persistent artifacts as MCP resources … `lmstxt://artifacts/<filename>`” → T6
  * “Agent checklist (do this every time)” → T1
  * “standard place … server’s initialization instructions (`InitializeResult.instructions`)” → T2
  * “Tool-level contract: `description` + `inputSchema` … constraints … `isError` …” → T3
  * “Safety/behavior hints: `ToolAnnotations` …” → T4
  * “Workflow guidance as first-class MCP objects: ‘Prompts’ …” → T5
  * “Long-form docs as MCP ‘Resources’ … expose `lmstxt://docs/usage` …” → T6
* Dependencies:

  * T6 depends on T1 because the usage doc content is served via MCP resources.
  * T2 depends on T6 because `InitializeResult.instructions` is recommended to stay short and link to a full docs resource.
* Split Tickets:

```ticket T1
T# Title:
- Publish and maintain `lmstxt-usage.md` as agent-facing MCP usage guidance

Type:
- docs

Target Area:
- Documentation: `lmstxt-usage.md` (agent/assistant guidance for lmstxt MCP)

Summary:
- Create/refresh the agent-facing usage doc so an agent can reliably select the right lmstxt tools, provide correct inputs, and recover from common failures. The content must explicitly cover repo URL validity, server-side artifact paths, run-based reads, supported artifact names, and end-to-end workflows.

In Scope:
- Define what `lmstxt` does and where artifacts are stored (server machine artifacts directory).
- Document supported `artifact_name` values (`llms.txt`, `llms-full.txt`, `llms-ctx.txt`, `llms.json`).
- Document required inputs and non-negotiable rules:
  - `repo_url` must be owner/repo (org-only rejected).
  - `output_dir` is server-side and must be under `LLMSTXT_MCP_ALLOWED_ROOT`; best practice to omit unless known-correct.
  - Prefer `run_id` reads after generation.
- Document artifact file naming convention: `<output_dir>/<owner>/<repo>/<repo>-<artifact_name>`.
- Provide “Quick workflows” call sequences (read existing; generate then read; generate derived artifacts).
- Include “Common failures (and the correct agent response)” section (URL invalid, output dir not allowed, LM Studio unavailable, artifact not found).
- Include “Agent checklist” section.

Out of Scope:
- Not provided

Current Behavior (Actual):
- Not provided

Expected Behavior:
- Agents can follow the doc to:
  - choose the correct tool sequence
  - provide valid inputs on first attempt
  - correct themselves based on known failure messages

Reproduction Steps:
- Not provided

Requirements / Constraints:
- Must explicitly state the repo URL constraint (owner/repo, not org-only).
- Must explicitly state `output_dir` is server-side and constrained by `LLMSTXT_MCP_ALLOWED_ROOT`.
- Must explicitly list allowed `artifact_name` values.

Evidence:
- Common failures enumerated in the doc: “Unrecognized GitHub URL”, “Output directory not allowed”, “LM Studio unavailable”, “Artifact not found”.

Open Items / Unknowns:
- Where (repo path) the documentation is hosted is not provided.
- Whether the doc should be exposed only as a repo file, or also as an MCP resource (covered by T6).

Risks / Dependencies:
- Depends on accurate tool contracts; mismatches between doc and tool schemas cause confusion (see T3).

Acceptance Criteria:
- [ ] `lmstxt-usage.md` contains: purpose, artifacts list, required input rules, artifact naming convention, quick workflows, tool usage notes, common failures, agent checklist.
- [ ] The doc explicitly states `repo_url` must be owner/repo and that org-only URLs are rejected.
- [ ] The doc explicitly states `output_dir` is server-side and constrained by `LLMSTXT_MCP_ALLOWED_ROOT`.
- [ ] The doc explicitly lists allowed `artifact_name` values.

Priority & Severity (if inferable from input text):
- Priority: Not provided
- Severity: Not provided

Source:
- “build on the `lmstxt-usage.md` … clear on how to use the lmstxt mcp tools …”
- “`repo_url` must be a *repository* URL … org-only URLs are rejected”
- “`output_dir` is … inside … `LLMSTXT_MCP_ALLOWED_ROOT`”
```

```ticket T2
T# Title:
- Add server initialization guidance via `InitializeResult.instructions`

Type:
- docs

Target Area:
- MCP server initialization response (`initialize` → `instructions`)

Summary:
- Provide short, high-signal operating rules and a “happy path” in the MCP server’s initialization instructions so clients can inject the guidance at connect time. Keep the instructions concise and point to fuller documentation via MCP resources (see T6).

In Scope:
- Add `InitializeResult.instructions` content that includes:
  - 5–20 non-negotiables (required inputs, ordering constraints, path rules)
  - a minimal happy path for typical workflows
  - minimal environment/config notes (kept concise)

Out of Scope:
- Full long-form documentation content (served as resources; see T6)
- Not provided

Current Behavior (Actual):
- Not provided

Expected Behavior:
- On MCP initialize, clients receive a concise instructions string that improves agent correctness for tool usage and sequencing.

Reproduction Steps:
- Not provided

Requirements / Constraints:
- Instructions must be short and focused.
- Must reflect the documented key rules (repo URL validity, server-side `output_dir` constraints, prefer `run_id` after generation).

Evidence:
- The guidance explicitly calls out `InitializeResult.instructions` as the canonical slot for agent-facing usage rules.

Open Items / Unknowns:
- Exact server framework/implementation details are not provided.

Risks / Dependencies:
- Depends on T6 if instructions are expected to reference an MCP resource for full docs.

Acceptance Criteria:
- [ ] MCP `initialize` response includes a non-empty `instructions` string.
- [ ] Instructions include the core non-negotiables (repo URL, server-side output dir constraint, run_id preference).
- [ ] Instructions remain concise (rules + happy path), with full docs deferred to a resource (if implemented).

Priority & Severity (if inferable from input text):
- Priority: Not provided
- Severity: Not provided

Source:
- “Server-level ‘user manual’: `InitializeResult.instructions` (the canonical slot)”
- “Keep `InitializeResult.instructions` short … link to a resource for full docs”
```

```ticket T3
T# Title:
- Align tool descriptions and `inputSchema` contracts with required inputs and error self-correction

Type:
- chore

Target Area:
- MCP tool definitions (descriptions, JSON Schema `inputSchema`, error signaling)

Summary:
- Make tool contracts self-describing and machine-checkable so agents cannot easily call tools with invalid inputs. Encode required-vs-optional fields via schema, constrain enumerations/patterns, and ensure tool errors return `isError=true` plus a corrective message.

In Scope:
- Ensure each tool has an explicit, accurate `description`.
- Ensure each tool has a JSON Schema `inputSchema` that:
  - marks required fields via `required`
  - constrains known enums (e.g., `artifact_name`)
  - applies constraints where possible (patterns/minLength) to reduce ambiguous inputs
- Ensure errors are surfaced via tool results (`isError=true`) with guidance on how to fix inputs.
- Apply to the documented tools:
  - `lmstxt_generate_llms_txt` (requires `url`; optional `output_dir`, `cache_lm`)
  - `lmstxt_generate_llms_full` (requires `repo_url`; optional `run_id`, `output_dir`)
  - `lmstxt_generate_llms_ctx` (requires `repo_url` when `run_id` omitted; optional `output_dir`)
  - `lmstxt_list_runs` (optional `limit`, default 10; max 50)
  - `lmstxt_list_all_artifacts` (no inputs; returns artifact metadata including a resource `uri`)
  - `lmstxt_read_artifact` (requires `artifact_name`; `repo_url` required when `run_id` omitted; supports `offset`, `limit`)

Out of Scope:
- Adding new tools not mentioned in the doc
- Not provided

Current Behavior (Actual):
- Not provided

Expected Behavior:
- Tool contracts unambiguously communicate what inputs are required and constrained, and error responses are actionable for self-correction.

Reproduction Steps:
- Not provided

Requirements / Constraints:
- Must encode “required vs optional” unambiguously in `inputSchema.required`.
- Must constrain `artifact_name` to the documented set.
- Must support error self-correction via `isError`.

Evidence:
- The guidance explicitly emphasizes using `inputSchema` constraints and returning tool errors with `isError`.

Open Items / Unknowns:
- Exact current tool schema/content is not provided.

Risks / Dependencies:
- Not provided

Acceptance Criteria:
- [ ] Each documented tool exposes a `description` and `inputSchema`.
- [ ] `artifact_name` is schema-constrained to `llms.txt`, `llms-full.txt`, `llms-ctx.txt`, `llms.json`.
- [ ] Schemas explicitly mark required fields (e.g., `url` for generate, `artifact_name` for read).
- [ ] Invalid-input scenarios produce `isError=true` and a corrective message.

Priority & Severity (if inferable from input text):
- Priority: Not provided
- Severity: Not provided

Source:
- “Tool definitions are meant to be self-describing … `description` and … `inputSchema`”
- “Make required vs optional unambiguous via `inputSchema.required`”
- “MCP recommends tool errors be surfaced … (`isError`) so the model can self-correct”
```

```ticket T4
T# Title:
- Add `ToolAnnotations` safety/side-effect hints for lmstxt tools

Type:
- chore

Target Area:
- MCP `ToolAnnotations` for tools (readOnly/destructive/idempotent/openWorld hints)

Summary:
- Add standardized ToolAnnotations hints so clients/models can reason about side effects and safety. In particular, mark tools that write files as not read-only and set destructive hints based on overwrite behavior.

In Scope:
- Add `ToolAnnotations` for tools, including:
  - `readOnlyHint`
  - `destructiveHint`
  - `idempotentHint`
  - `openWorldHint`
- Ensure file-writing tools are annotated as `readOnlyHint=false`.
- Set `destructiveHint` according to whether a tool overwrites existing files (as described).

Out of Scope:
- Changing actual tool behavior (only annotations)
- Not provided

Current Behavior (Actual):
- Not provided

Expected Behavior:
- Tools expose standardized annotation hints that reflect whether they read-only vs write, and whether they may be destructive.

Reproduction Steps:
- Not provided

Requirements / Constraints:
- Must follow the documented intent: writing tools `readOnlyHint=false`, destructive depends on overwrite behavior.

Evidence:
- The guidance calls out ToolAnnotations and explicitly notes the file-writing case.

Open Items / Unknowns:
- Whether tools overwrite existing artifacts is not provided.

Risks / Dependencies:
- Not provided

Acceptance Criteria:
- [ ] Tools expose ToolAnnotations.
- [ ] Tools that write artifacts are annotated `readOnlyHint=false`.
- [ ] `destructiveHint` is set consistently with overwrite semantics (as implemented).

Priority & Severity (if inferable from input text):
- Priority: Not provided
- Severity: Not provided

Source:
- “Safety/behavior hints: `ToolAnnotations` … `readOnlyHint`, `destructiveHint` …”
- “mark anything that writes files as `readOnlyHint=false` … `destructiveHint` … if it overwrites”
```

```ticket T5
T# Title:
- Provide MCP “Prompts” for standard lmstxt workflows to prevent improvised tool sequences

Type:
- enhancement

Target Area:
- MCP server prompts (discoverable prompt templates)

Summary:
- Add first-class MCP prompts that encode the intended tool-call sequences for repeatable workflows (generate then read; generate derived artifacts). This reduces agent errors by giving a canonical, structured workflow rather than relying on free-form planning.

In Scope:
- Expose prompt templates for repeatable workflows mentioned in the guidance, such as:
  - Generate `llms.txt` then read by `run_id`
  - Generate `llms-full.txt` / `llms-ctx.txt` from an existing `llms.txt` then read
  - Read existing artifacts (optionally list first)
- Prompts should specify which tools to call and which inputs must be provided.

Out of Scope:
- Not provided

Current Behavior (Actual):
- Not provided

Expected Behavior:
- MCP clients can discover and apply prompts that guide agents through correct tool sequences without improvisation.

Reproduction Steps:
- Not provided

Requirements / Constraints:
- Prompts must align with the documented workflows and tool names/inputs.

Evidence:
- The guidance explicitly recommends MCP prompts as a clean way to prevent agents from inventing sequences.

Open Items / Unknowns:
- Exact prompt catalog naming conventions are not provided.

Risks / Dependencies:
- Depends on accurate tool contracts (see T3).

Acceptance Criteria:
- [ ] MCP server exposes at least the core workflow prompts described above.
- [ ] Each prompt encodes a clear, correct tool-call order and required inputs.
- [ ] Prompts reference the same tool names and input expectations as the documented tool reference.

Priority & Severity (if inferable from input text):
- Priority: Not provided
- Severity: Not provided

Source:
- “Workflow guidance as first-class MCP objects: ‘Prompts’”
- “prevent agents from improvising the wrong tool sequence … explicitly say which tool to call … in what order”
```

```ticket T6
T# Title:
- Expose long-form usage guidance and artifact reads via MCP Resources

Type:
- enhancement

Target Area:
- MCP server resources (docs resources + artifact resources)

Summary:
- Provide MCP Resources so clients can fetch long-form documentation and cached artifacts through standardized URIs. This includes serving the usage doc as `lmstxt://docs/usage` (or similar) and enabling artifact resource URIs like `lmstxt://artifacts/<filename>` returned by `lmstxt_list_all_artifacts`.

In Scope:
- Expose the full usage doc as an MCP resource (e.g., `lmstxt://docs/usage`).
- Optionally expose smaller per-tool docs resources (e.g., `lmstxt://docs/tools/generate`, etc.) as described.
- Ensure `lmstxt_list_all_artifacts` includes a `uri` field for each artifact (resource URI) and that clients can read it.
- Support artifact resource URI form: `lmstxt://artifacts/<filename>` as described.

Out of Scope:
- Not provided

Current Behavior (Actual):
- Not provided

Expected Behavior:
- Clients can read long-form docs and cached artifacts via resource URIs without needing to rely solely on runs.

Reproduction Steps:
- Not provided

Requirements / Constraints:
- Resources should be read-only for documentation.
- Resource URIs must match the documented patterns (`lmstxt://docs/...`, `lmstxt://artifacts/...`).

Evidence:
- The guidance explicitly recommends resources for long-form docs and documents the artifact URI pattern.

Open Items / Unknowns:
- How resources are mapped internally to file system paths is not provided.

Risks / Dependencies:
- Depends on T1 to provide the definitive doc content for the `docs/usage` resource.

Acceptance Criteria:
- [ ] MCP server exposes a docs resource for the usage guide (e.g., `lmstxt://docs/usage`).
- [ ] `lmstxt_list_all_artifacts` returns a resource `uri` per artifact.
- [ ] Artifact resource URIs follow the documented pattern and are readable by clients that support resources.

Priority & Severity (if inferable from input text):
- Priority: Not provided
- Severity: Not provided

Source:
- “Long-form docs as MCP ‘Resources’ … expose `lmstxt://docs/usage`”
- “`lmstxt_list_all_artifacts` returns a `uri` like … `lmstxt://artifacts/<filename>`”
- “Some clients can read resources directly using that URI”
```
