# lmstxt MCP quick use (agent handoff)

## Goal

Read a repo’s `llms.txt` (or `llms-full.txt`, `llms-ctx.txt`) via the lmstxt MCP.

## 1) Use a full repo URL

Use a **repository** URL, not an org:

- ✅ `https://github.com/charmbracelet/glow`
- ❌ `https://github.com/charmbracelet`

## 2) Read directly (preferred)

Call `lmstxt_read_artifact` with the repo URL and desired artifact:

```json
{
  "tool": "mcp__lmstxt__lmstxt_read_artifact",
  "args": {
    "repo_url": "https://github.com/charmbracelet/glow",
    "output_dir": "/home/user/projects/temp/lms-llmsTxt/artifacts",
    "artifact_name": "llms.txt",
    "offset": 0,
    "limit": 4000
  }
}
```

## 3) Choose an artifact type

Set `artifact_name` to one of:

- `llms.txt` (default summary)
- `llms-full.txt` (expanded)
- `llms-ctx.txt` (context-heavy)

## 4) If read fails, generate once

If the read tool reports missing/unrecognized repo, generate the artifacts and then read:

```json
{
  "tool": "mcp__lmstxt__lmstxt_generate_llms_txt",
  "args": {
    "url": "https://github.com/charmbracelet/glow",
    "output_dir": "/home/user/projects/temp/lms-llmsTxt/artifacts"
  }
}
```

Then re-run the read from step 2.

## 5) (Optional) list cached artifacts

To see what’s already cached:

```json
{
  "tool": "mcp__lmstxt__lmstxt_list_all_artifacts",
  "args": {}
}
```

## Notes

- Always prefer deterministic read via `repo_url` + `artifact_name`.
- If you need just a slice, adjust `offset` and `limit`.

---

## UPDATED/REVISED VERSION (NEEDS REVIEW BY CODE BASE AGENT TO VERIFY CORRECT USAGE)

[Download updated lmstxt-usage.md](sandbox:/mnt/data/lmstxt-usage.updated.md)

This version removes the placeholder `...` sections and makes the MCP tool inputs/constraints explicit (including the org-vs-repo URL failure that caused the earlier mistake). MCP tool discovery/call semantics are aligned with the MCP spec (tools expose input schemas; clients call them via `tools/list` / `tools/call`).  The `llms.txt` concept is based on the public proposal for LLM-oriented site/repo indexes.

````md
# lmstxt MCP usage (agent guidance)

This document is written for **agents/assistants** that can call MCP tools. It defines:
- what inputs are required,
- which tool to call for each goal,
- and the common failure modes to avoid.

---

## What lmstxt does

`lmstxt` is an MCP server that generates and reads **repo documentation artifacts** (files) for a GitHub repository, stored under a local **artifacts directory** on the **machine where the MCP server is running**.

### Artifacts you can read

`artifact_name` must be one of:

- `llms.txt` — concise “index” file for LLMs
- `llms-full.txt` — expanded/full context file derived from `llms.txt`
- `llms-ctx.txt` — additional context file (if enabled)
- `llms.json` — structured metadata

---

## Required inputs (and the rules that prevent mistakes)

### 1) `repo_url` must be a *repository* URL
Use a full owner/repo URL:

- ✅ `https://github.com/charmbracelet/glow`
- ✅ `git@github.com:charmbracelet/glow.git`
- ❌ `https://github.com/charmbracelet` (org-only URLs are rejected)

If the user gives an org URL or an ambiguous repo name, **ask for the exact repo URL**.

### 2) `output_dir` is a server-side path and must be allowed
`output_dir` is interpreted on the machine where the **MCP server runs**, not the client UI.

- It must be inside the server’s configured allowed root (`LLMSTXT_MCP_ALLOWED_ROOT`).
- If you see an “output directory not allowed” style error, you must change `output_dir` (or the server config) — not “try harder”.

**Best practice:** omit `output_dir` unless you have a known-correct value for the current environment.

### 3) `run_id` vs `repo_url`
Some tools can work in either mode:

- **Run mode (`run_id`)**: most deterministic; refers to a recorded generation run.
- **Direct disk mode (`repo_url` + `output_dir`)**: reads artifacts by computing the expected file path.

**Best practice:** prefer `run_id` if you generated the artifacts in the same session.

### 4) Artifact file naming (what you’ll see in caches)
Artifacts are written under:

`<output_dir>/<owner>/<repo>/<repo>-<artifact_name>`

Examples:
- `.../artifacts/charmbracelet/glow/glow-llms.txt`
- `.../artifacts/charmbracelet/glow/glow-llms-full.txt`

---

## Quick workflows (copy/paste recipes)

The examples below show two common call styles:

- **Generic MCP style** (tool `name` + `input`)
- **Namespaced tool style** (some clients prefix tool names, e.g. `mcp__lmstxt__...`)

Use the one that matches your client.

### A) Read an existing artifact (no generation)
Use this when you believe the artifact already exists on disk.

1) (Optional) list what exists:
```json
{
  "name": "lmstxt_list_all_artifacts",
  "input": {}
}
````

1. Read the artifact you want:

```json
{
  "name": "lmstxt_read_artifact",
  "input": {
    "repo_url": "https://github.com/charmbracelet/glow",
    "artifact_name": "llms.txt",
    "offset": 0,
    "limit": 10000
  }
}
```

### B) Generate `llms.txt`, then read it (recommended end-to-end)

1. Start generation:

```json
{
  "name": "lmstxt_generate_llms_txt",
  "input": {
    "url": "https://github.com/charmbracelet/glow",
    "cache_lm": true
  }
}
```

1. Poll until complete:

```json
{
  "name": "lmstxt_list_runs",
  "input": { "limit": 10 }
}
```

1. Read by `run_id` (preferred):

```json
{
  "name": "lmstxt_read_artifact",
  "input": {
    "run_id": "<RUN_ID_FROM_GENERATION>",
    "artifact_name": "llms.txt",
    "offset": 0,
    "limit": 10000
  }
}
```

### C) Generate `llms-full.txt` or `llms-ctx.txt`

These are derived from `llms.txt`, so ensure `llms.txt` exists first.

Generate `llms-full.txt`:

```json
{
  "name": "lmstxt_generate_llms_full",
  "input": {
    "repo_url": "https://github.com/charmbracelet/glow",
    "run_id": "<RUN_ID_WITH_LLMS_TXT>"
  }
}
```

Generate `llms-ctx.txt`:

```json
{
  "name": "lmstxt_generate_llms_ctx",
  "input": {
    "repo_url": "https://github.com/charmbracelet/glow",
    "run_id": "<RUN_ID_WITH_LLMS_TXT>"
  }
}
```

Then read the new artifact with `lmstxt_read_artifact`.

---

## Tool reference (what to call and what inputs are required)

### `lmstxt_generate_llms_txt`

Generate the initial `llms.txt` artifact for a repo.

**Inputs**

- `url` (required): GitHub repo URL
- `output_dir` (optional): artifacts root on the server (default `./artifacts`)
- `cache_lm` (optional): enable LM caching (default `true`)

**Output**

- JSON string representing a `RunRecord` (includes `run_id`, `status`, and `artifacts` list once completed)

---

### `lmstxt_generate_llms_full`

Generate `llms-full.txt` from an existing `llms.txt`.

**Inputs**

- `repo_url` (required)
- `run_id` (optional): a run that already contains `llms.txt`
- `output_dir` (optional): used if `run_id` is omitted

**Output**

- JSON string `RunRecord`

---

### `lmstxt_generate_llms_ctx`

Generate `llms-ctx.txt` from an existing `llms.txt`.

**Inputs**

- `run_id` (optional)
- `repo_url` (required when `run_id` is omitted)
- `output_dir` (optional): used if `run_id` is omitted

**Output**

- JSON string `RunRecord`

---

### `lmstxt_list_runs`

List recent run records (newest first).

**Inputs**

- `limit` (optional, default 10; max 50)

**Output**

- JSON list of `RunRecord` objects

---

### `lmstxt_list_all_artifacts`

List all persistent `.txt` artifacts under the server’s allowed root.

**Inputs**

- none

**Output**

- JSON list of artifact metadata objects, including a resource `uri` you can read in clients that support MCP resources.

---

### `lmstxt_read_artifact`

Read the contents of a generated artifact.

**Inputs**

- `artifact_name` (required): one of `llms.txt`, `llms-full.txt`, `llms-ctx.txt`, `llms.json`
- `run_id` (optional)
- `repo_url` (required when `run_id` is omitted)
- `output_dir` (optional): used when `run_id` is omitted
- `offset` (optional): start position (byte offset)
- `limit` (optional): max characters returned (also capped by server max)

**Output**

- The artifact’s text content (may be truncated for large files)

---

## Common failures (and the correct agent response)

### “Unrecognized GitHub URL”

Cause: org-only URL or malformed URL.

Fix: Ask for a full repo URL and retry:

- `https://github.com/<owner>/<repo>`

### “Output directory not allowed”

Cause: `output_dir` is outside `LLMSTXT_MCP_ALLOWED_ROOT`.

Fix:

- Remove `output_dir` (use default), or
- Set `output_dir` to a path under the allowed root, or
- Reconfigure the server’s allowed root.

### “LM Studio unavailable” / connection errors

Cause: generation tools need LM Studio reachable from the server.

Fix:

- Ensure LM Studio is running, and
- Ensure `LMSTUDIO_BASE_URL` matches the server’s network reality (e.g. `http://localhost:1234/v1` on the same machine).

### “Artifact not found”

Cause: you tried to read `llms.txt` before generating it, or pointed at the wrong `output_dir`.

Fix:

- Generate `llms.txt` first, then read by `run_id`.

---

## Advanced: reading persistent artifacts as MCP resources

`lmstxt_list_all_artifacts` returns a `uri` like:

- `lmstxt://artifacts/<filename>`

Some clients can read resources directly using that URI. Use this when you want to fetch a cached artifact without using runs.

---

## Agent checklist (do this every time)

1. Validate the URL is `owner/repo`, not org-only.
2. Decide: **read existing** vs **generate then read**.
3. Prefer `run_id` reads after generation.
4. Use exact `artifact_name` values.
5. Treat `output_dir` as server-side and avoid cross-OS path assumptions.
