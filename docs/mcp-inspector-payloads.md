# MCP inspector payloads

Use these payloads with the MCP Inspector to verify the `lmstxt-mcp` server tools. The tool names and inputs are grounded in `src/lms_llmsTxt_mcp/server.py`.

Start the inspector from the repository root:

```bash
npx @modelcontextprotocol/inspector --config ./inspector.config.json --server lmstxt
```

## Generate `llms.txt`

```json
{
  "url": "https://github.com/pallets/flask",
  "output_dir": "./artifacts",
  "cache_lm": true,
  "generate_graph": true,
  "verbose_budget": false
}
```

Call with tool name: `lmstxt_generate_llms_txt`.

## List recent runs

```json
{
  "limit": 10
}
```

Call with tool name: `lmstxt_list_runs`.

## Read an artifact by run id

```json
{
  "run_id": "<run-id-from-generation>",
  "artifact_name": "llms.txt",
  "offset": 0,
  "limit": 10000
}
```

Call with tool name: `lmstxt_read_artifact`.

## Read an artifact by repository URL

```json
{
  "repo_url": "https://github.com/pallets/flask",
  "output_dir": "./artifacts",
  "artifact_name": "llms-full.txt",
  "offset": 0,
  "limit": 10000
}
```

Call with tool name: `lmstxt_read_artifact`.

## Generate `llms-full.txt`

```json
{
  "repo_url": "https://github.com/pallets/flask",
  "run_id": "<run-id-with-llms-txt>",
  "output_dir": "./artifacts"
}
```

Call with tool name: `lmstxt_generate_llms_full`.

## Generate `llms-ctx.txt`

```json
{
  "run_id": "<run-id-with-llms-txt>",
  "repo_url": "https://github.com/pallets/flask",
  "output_dir": "./artifacts"
}
```

Call with tool name: `lmstxt_generate_llms_ctx`.

## List persistent text artifacts

```json
{}
```

Call with tool name: `lmstxt_list_all_artifacts`.

## List graph artifacts

```json
{}
```

Call with tool name: `lmstxt_list_graph_artifacts`.

## Read a graph artifact

Use a filename returned by `lmstxt_list_graph_artifacts`.

```json
{
  "filename": "pallets/flask/graph/repo.graph.json",
  "offset": 0,
  "limit": 10000
}
```

Call with tool name: `lmstxt_read_graph_artifact`.

## Read a graph node

Use a `repo_id` and `node_id` returned by graph artifact listings or graph JSON.

```json
{
  "repo_id": "pallets--flask",
  "node_id": "moc",
  "offset": 0,
  "limit": 10000
}
```

Call with tool name: `lmstxt_read_repo_graph_node`.

## Validation notes

- Use full repository URLs, not organization-only URLs.
- Keep `output_dir` under `LLMSTXT_MCP_ALLOWED_ROOT`.
- Prefer `run_id` reads after a generation call because they refer to the recorded run.
- `artifact_name` must be one of `llms.txt`, `llms-full.txt`, `llms-ctx.txt`, or `llms.json`.
- `limit` is capped by `LLMSTXT_MCP_RESOURCE_MAX_CHARS` even when a larger value is passed.
