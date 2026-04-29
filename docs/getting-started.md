# Getting Started

This guide helps you run the project locally and understand the first few things to explore.

## What This Project Does

`lms-llmsTxt` generates LLM-friendly repository documentation artifacts:

- `llms.txt` (curated summary/index)
- `llms-full.txt` (expanded content)
- optional `llms-ctx.txt`
- repository graph artifacts (`repo.graph.json`, `repo.force.json`, `nodes/*.md`)

It can be used either as a CLI tool (`lmstxt`) or through an MCP server (`lmstxt-mcp`).

## 5-Minute Setup

### 1) Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2) Install dependencies

```bash
pip install -e '.[dev]'
```

### 3) Start LM Studio server

```bash
lms server start --port 1234
```

### 4) Configure auth (for private repos)

```bash
export GITHUB_ACCESS_TOKEN="ghp_..."
```

### 5) Run the CLI once

```bash
PYTHONPATH=src lmstxt https://github.com/pallets/flask --graph-only --generate-graph
```

You should see generated files under `artifacts/<owner>/<repo>/`.

### 6) Start the graph visualizer (repo root)

```bash
npm --prefix hypergraph install
npm run ui:dev
```

Open `http://localhost:3000`.

## First Commands You Will Use

### Run targeted tests

```bash
pytest -q tests/test_analyzer.py tests/test_mcp_stdio.py tests/test_mcp_tool_execution.py
```

### Run full test suite

```bash
pytest
```

### Start MCP server

```bash
lmstxt-mcp
```

### CLI -> Visualizer handoff

```bash
PYTHONPATH=src lmstxt https://github.com/pallets/flask \
  --graph-only \
  --generate-graph \
  --ui
```

The CLI prints a HyperGraph URL that pre-fills `graphPath` and auto-loads the generated `repo.graph.json`.
It also auto-starts/reuses the HyperGraph UI and opens your browser by default.

Use `--ui-no-open` if you only want the URL and background UI startup behavior.

### UI-first repo generation

In HyperGraph (`http://localhost:3000`):

1. Open **Generate repo graph**
2. Enter a GitHub repo URL (for example `https://github.com/pallets/flask`)
3. Run generation and inspect the resulting graph directly in the viewer

You can also use **Load repo graph** with a path like `../artifacts/<owner>/<repo>/graph/repo.graph.json`.

## Project Tour

```text
src/
  lms_llmsTxt/           Core generation pipeline and analyzers
  lms_llmsTxt_mcp/       MCP server, tools, and resource handlers
tests/                   Unit/integration test suite
artifacts/               Generated outputs from CLI/MCP runs
docs/                    Operational and architecture docs
```

Key files to read first:

1. `src/lms_llmsTxt/cli.py` - CLI arguments and entrypoint behavior
2. `src/lms_llmsTxt/pipeline.py` - orchestration and fallback behavior
3. `src/lms_llmsTxt/analyzer.py` - DSPy-driven summarization
4. `src/lms_llmsTxt_mcp/server.py` - MCP tools/resources

## Typical Development Workflow

1. Create a branch.
2. Implement changes in `src/`.
3. Add/update tests in `tests/`.
4. Run targeted tests first, then full suite.
5. Validate one real CLI run against a public repo.

## Common Issues

### `lmstxt-mcp` not found

Use module fallback:

```bash
PYTHONPATH=src python3 -m lms_llmsTxt_mcp.server
```

### LM Studio connection errors

- Ensure server is running on `http://localhost:1234/v1`
- Ensure selected model exists in LM Studio

### Missing GitHub content on private repos

- Verify `GITHUB_ACCESS_TOKEN` or `GH_TOKEN` is set
- Confirm token has contents/metadata access
