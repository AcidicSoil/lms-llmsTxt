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
