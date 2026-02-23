---
title: "LM Studio llms.txt Generator"
description: "Generate llms.txt, llms-full, and fallback artifacts for GitHub repositories using DSPy with LM Studio."
---

[![PyPI](https://img.shields.io/pypi/v/lms-llmstxt)](https://pypi.org/project/lms-llmsTxt/) [![Downloads](https://img.shields.io/pypi/dm/lms-llmstxt)](https://pypi.org/project/lms-llmsTxt/) [![TestPyPI](https://img.shields.io/badge/TestPyPI-lms--llmsTxt-informational)](https://test.pypi.org/project/lms-llmsTxt/) [![CI](https://github.com/AcidicSoil/lms-llmsTxt/actions/workflows/release.yml/badge.svg?branch=main)](https://github.com/AcidicSoil/lms-llmsTxt/actions/workflows/release.yml) [![Repo](https://img.shields.io/badge/GitHub-AcidicSoil%2Flms--llmsTxt-181717?logo=github)](https://github.com/AcidicSoil/lms-llmsTxt)
[![LM Studio Hub](https://img.shields.io/badge/LM%20Studio%20Hub-%40dirty--data-blue)](https://lmstudio.ai/dirty-data)
[![GitHub](https://img.shields.io/badge/GitHub-AcidicSoil-181717?logo=github)](https://github.com/AcidicSoil)


## Overview

Use this CLI-first toolkit to produce LLM-friendly documentation bundles (`llms.txt`, `llms-full.txt`, optional `llms-ctx.txt`, and fallback JSON) for any GitHub repository. The generator wraps DSPy analyzers, manages LM Studio model lifecycle with the official Python SDK, and guarantees output even when the primary language model cannot respond.

> [!NOTE]
> The pipeline validates curated links, detects default branches automatically, and writes artifacts to `artifacts/<owner>/<repo>/`.

## Prerequisites

- Python 3.10 or later
- LM Studio server available locally (Developer tab → **Start Server**) or the CLI (`lms server start --port 1234`)
- GitHub API token in `GITHUB_ACCESS_TOKEN` or `GH_TOKEN`
- Optional: [`llms_txt`](https://pypi.org/project/llms-txt/) when you want to produce `llms-ctx.txt`

> [!WARNING]
> Install dependencies inside a virtual environment to avoid PEP 668 “externally managed environment” errors.

## Install

### Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Using uv:

```bash
uv venv
source .venv/bin/activate
```

### Install the package with developer extras

```bash
pip install -e '.[dev]'
```

Using uv:

```bash
uv pip install -e '.[dev]'
```

Installing the editable package exposes the `lmstxt` CLI and the `lmstxt-mcp` server.

> [!TIP]
> Keep the virtual environment active while running the CLI or tests so the SDK-based unload logic can import `lmstudio`.

## Configure LM Studio

### Load the CLI and start the server

```bash
npx lmstudio install-cli
lms server start --port 1234
```

The server must expose an OpenAI-compatible endpoint, commonly `http://localhost:1234/v1`.

### Ensure the target model is downloaded

Open LM Studio, download the model (for example `qwen/qwen3-4b-2507`), and confirm it appears in the **Server** tab.

## Quick start

Run the CLI against any GitHub repository:

```bash
lmstxt https://github.com/owner/repo \
  --model qwen/qwen3-4b-2507 \
  --api-base http://localhost:1234/v1 \
  --stamp
```

The command writes artifacts to `artifacts/owner/repo/`. Use `--output-dir` to override the destination.

To print a HyperGraph viewer handoff URL after graph generation:

```bash
lmstxt https://github.com/owner/repo \
  --generate-graph \
  --graph-only \
  --ui
```

This prints a URL like `http://localhost:3000/?mode=load-repo-graph&graphPath=...&autoLoad=1`.

## Private GitHub repositories

To run against a private repository you own, the GitHub API calls must be authenticated. The CLI reads a token from `GITHUB_ACCESS_TOKEN` or `GH_TOKEN` and sends it as a `Bearer` token.

Token options:

- **Classic PAT**: grant at least `repo` scope for private repo read access.
- **Fine-grained PAT**: grant read access to **Contents** and **Metadata** for the target repo.
- **Org SSO**: if your org enforces SSO, you must authorize the token in the GitHub SSO UI.

Environment setup examples:

```bash
export GITHUB_ACCESS_TOKEN="ghp_..."
# or
export GH_TOKEN="ghp_..."
```

You can also use a `.env` file; the CLI calls `load_dotenv()` on startup and reads the token into `AppConfig.github_token`.

```bash
GITHUB_ACCESS_TOKEN=ghp_...
```

Run the CLI normally once the token is available:

```bash
lmstxt https://github.com/<owner>/<repo>
```

If you run the MCP server, the same env vars must be present in the process environment that launches `lmstxt-mcp` (for example, in your MCP client config).

### Environment variables

| Variable | Description |
|----------|-------------|
| `LMSTUDIO_MODEL` | Default LM Studio model identifier |
| `LMSTUDIO_BASE_URL` | Base URL such as `http://localhost:1234/v1` |
| `LMSTUDIO_API_KEY` | API key for secured LM Studio deployments |
| `OUTPUT_DIR` | Custom root directory for artifacts |
| `ENABLE_CTX=1` | Emit `llms-ctx.txt` using the optional `llms_txt` package |

## Generated artifacts

| Artifact | Purpose |
|----------|---------|
| `*-llms.txt` | Primary documentation synthesized by DSPy or the fallback heuristic |
| `*-llms-full.txt` | Expanded content fetched from curated GitHub links with 404 filtering |
| `*-llms.json` | Fallback JSON following `LLMS_JSON_SCHEMA` (only when LM fallback triggers) |
| `*-llms-ctx.txt` | Optional context file created when `ENABLE_CTX=1` and `llms_txt` is installed |

> [!IMPORTANT]
> The pipeline always writes `llms.txt` and `llms-full.txt`, even when the language model call fails.

## Graph visualizer (HyperGraph)

Use the built-in HyperGraph UI to inspect and generate `repo.graph.json` artifacts.

```bash
npm --prefix hypergraph install
npm run ui:dev
```

Open <http://localhost:3000>. You now have three flows:

- **Topic graph**: existing HyperGraph topic generation (Hyperbrowser + OpenAI).
- **Generate repo graph**: run the local `lms_llmsTxt` pipeline from the UI using a GitHub repo URL.
- **Load repo graph**: inspect an existing artifact path.

For manual loading, use a path like:

```
../artifacts/<owner>/<repo>/graph/repo.graph.json
```

The CLI `--ui` flag prints a ready-to-open URL that pre-fills this path and auto-loads the graph.

## Model Context Protocol (MCP) Server

This package includes a FastMCP server that exposes the generator as an MCP tool and provides access to generated artifacts as resources.

### Features

- **Asynchronous Processing**: Tool calls return a `run_id` immediately while generation happens in the background.
- **Tools**:
  - `lmstxt_generate_llms_txt`: Trigger `llms.txt` generation.
  - `lmstxt_generate_llms_full`: Generate `llms-full.txt` from an existing run.
  - `lmstxt_generate_llms_ctx`: Generate `llms-ctx.txt` (requires `llms_txt`).
  - `lmstxt_list_runs`: View recent generation history and status.
  - `lmstxt_read_artifact`: Read generated files with pagination support.
  - `lmstxt_list_all_artifacts`: List all persistent `.txt` artifacts on disk.
  - `lmstxt_list_graph_artifacts`: List discovered graph artifacts (`repo.graph.json`, `repo.force.json`, `nodes/*.md`).
  - `lmstxt_read_graph_artifact`: Read graph artifact content with pagination.
  - `lmstxt_read_repo_graph_node`: Read a graph node by repo id and node id.
- **Resources**:
  - **Run-specific**: `lmstxt://runs/{run_id}/{artifact_name}`
  - **Persistent Directory**: `lmstxt://artifacts/{filename}` (e.g., `lmstxt://artifacts/owner/repo/repo-llms.txt`)
  - **Graph file**: `lmstxt://graphs/{filename}`
  - **Repo graph node**: `repo://{repo_id}/graph/nodes/{node_id}` (for example `repo://owner--repo/graph/nodes/moc`)

### Running the Server

```bash
# Default stdio transport
lmstxt-mcp
```

### Client Configuration

Add to your MCP client config (e.g., `claude_desktop_config.json` or `config.toml`):

#### Claude Desktop / Cursor

```json
{
  "mcpServers": {
    "lmstxt": {
      "command": "lmstxt-mcp",
      "env": {
        "GITHUB_ACCESS_TOKEN": "your_token",
        "LMSTUDIO_BASE_URL": "http://localhost:1234/v1"
      }
    }
  }
}
```

#### Codex / CLI (toml)

```toml
[mcp_servers.lmstxt]
command = "lmstxt-mcp"
startup_timeout_sec = 30
tool_timeout_sec = 30

[mcp_servers.lmstxt.env]
GITHUB_ACCESS_TOKEN = "your_token"
LMSTUDIO_BASE_URL = "http://localhost:1234/v1"
```

## How it works

1. **Collect repository material** – the GitHub client gathers the file tree, README, package files, repository visibility, and default branch.
2. **Prepare LM Studio** – the manager confirms the requested model is loaded, auto-loading if necessary.
3. **Generate documentation** – DSPy produces curated content; on LM failures the fallback serializer builds markdown and JSON directly.
4. **Assemble `llms-full`** – curated links are re-fetched via raw GitHub URLs for public repos or authenticated API calls for private ones, with validation to remove dead links.
5. **Unload models safely** – the workflow first uses the official `lmstudio` SDK (`model.unload()` or `list_loaded_models`), then falls back to HTTP and CLI unload requests.

## Project layout

- `src/lms_llmsTxt/` – core generation library, DSPy analyzers, and LM Studio helpers.
- `src/lms_llmsTxt_mcp/` – MCP server implementation, asynchronous worker, and resource providers.
- `tests/` – pytest coverage for the generator pipeline and MCP server.
- `artifacts/` – sample outputs from previous runs.

## Documentation Map

- `docs/getting-started.md` - beginner onboarding and first commands.
- `docs/architecture.md` - system design, data flow, and extension points.
- `docs/publishing.md` - publishing and release workflow notes.
- `docs/oracle-pack-2026-01-04.md` - repository knowledge pack reference.

## Verify your setup

```bash
source .venv/bin/activate
python -m pytest
```

Using uv:

```bash
source .venv/bin/activate
uv run pytest
```

All tests should pass, confirming URL validation, fallback handling, and MCP resource exposure.

## Reliability Validation (2026-02-23)

An end-to-end run was executed against `https://github.com/pallets/flask`:

```bash
PYTHONPATH=src python3 -m lms_llmsTxt.cli https://github.com/pallets/flask \
  --generate-graph \
  --graph-only \
  --verbose-budget \
  --output-dir artifacts
```

Observed results:

- Artifacts generated:
  - `artifacts/pallets/flask/flask-llms.txt`
  - `artifacts/pallets/flask/graph/repo.graph.json`
  - `artifacts/pallets/flask/graph/repo.force.json`
  - `artifacts/pallets/flask/graph/nodes/*.md`
- Sanitization check: no `<think>`, `<analysis>`, or `Reasoning:` markers found in generated outputs.
- Graph grounding check: `repo.graph.json` contained `21` nodes and `0` nodes with missing evidence.
- Runtime mode: generation completed through the primary analyzer path (no fallback artifact emitted).

### Failure-Rate SLO Baseline

- Artifact delivery SLO: `>= 99%` successful artifact generation per invocation (`llms.txt` + graph artifacts when `--generate-graph` is used).
- Sanitization SLO: `100%` of generated artifacts must be free of reasoning tags (`<think>`, `<analysis>`, `Reasoning:`).
- Graph evidence SLO: `100%` graph nodes should include at least one evidence entry.

Current baseline run met all three SLO checks above in primary-path mode.

## Build & verify a local package

Use this flow to rebuild locally and verify the installed CLI before tagging and publishing.

```bash
python3 -m pip install -U pip
python3 -m pip install build
python3 -m build
python3 -m pip install --force-reinstall dist/*.whl
lmstxt --help
```

Using uv:

```bash
uv pip install -U pip
uv pip install build
uv build
uv pip install --force-reinstall dist/*.whl
lmstxt --help
```

Note: this project uses `setuptools_scm`, so the version comes from git tags. Before tagging, you will see a post-release + date suffix.

## Troubleshooting

> [!WARNING]
> If `pip install -e .[dev]` fails with build tool errors, ensure `cmake` and necessary compilers are installed.

Using uv:

```bash
uv pip install -e '.[dev]'
```

> [!TIP]
> If the MCP server times out during generation, check `lmstxt_list_runs` to see if the background task is still processing. The `lmstxt_generate_*` tools return immediately to avoid client timeouts.

### MCP Inspector

```bash
npx @modelcontextprotocol/inspector --config ./inspector.config.json --server lmstxt
```

Use the payloads in `docs/mcp-inspector-payloads.md` to verify specific tool behaviors.
