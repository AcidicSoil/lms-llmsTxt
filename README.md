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

Install the tools for the part of the project you want to use:

| Area | Required tools |
|------|----------------|
| CLI and MCP server | Python 3.10 or later, `pip` or `uv` |
| LM Studio generation | LM Studio desktop app or `lms` CLI, with the local server running |
| GitHub repository access | `GITHUB_ACCESS_TOKEN` or `GH_TOKEN` for private repos or higher API limits |
| HyperGraph UI | Node.js, npm, and the UI dependencies under `hypergraph/` |
| Documentation site | pnpm, using the version pinned by `packageManager` in `package.json` |

> [!WARNING]
> Install Python dependencies inside a virtual environment to avoid PEP 668 “externally managed environment” errors.

## Install

Use the install helper for repeatable setup:

```bash
scripts/install.sh --help
```

Common setup flows:

```bash
# Released CLI and MCP server from PyPI
scripts/install.sh --pypi --uv

# Source checkout for development
scripts/install.sh --dev --uv

# Everything needed for local development, UI, docs, and ctx verification
scripts/install.sh --all --uv
```

Choose the manual install path below when you need to run each step yourself.

### Install the CLI from PyPI

Use this when you only need the released `lmstxt` CLI and `lmstxt-mcp` server:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install lms-llmsTxt
```

Using uv:

```bash
uv venv
source .venv/bin/activate
uv pip install lms-llmsTxt
```

Verify the console scripts are available:

```bash
lmstxt --help
lmstxt-mcp --help
```

### Install from source for development

Use this when working on the repository, running tests, or using unreleased code:

```bash
git clone https://github.com/AcidicSoil/lms-llmsTxt.git
cd lms-llmsTxt
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
```

Using uv:

```bash
git clone https://github.com/AcidicSoil/lms-llmsTxt.git
cd lms-llmsTxt
uv venv
source .venv/bin/activate
uv sync --extra dev
```

The Python project dependencies are declared in `pyproject.toml`. The runtime install includes DSPy, LiteLLM, LM Studio SDK, `requests`, `llms-txt`, `llm-ctx`, FastMCP, Pydantic, and Pydantic Settings. The `dev` extra adds pytest.

### Install HyperGraph UI dependencies

Use this when running `lmstxt --ui`, `lmstxt --generate-graph --ui`, or the standalone HyperGraph development server:

```bash
npm --prefix hypergraph install
```

Then start the UI directly when needed:

```bash
npm run ui:dev
```

The root `ui:*` scripts delegate into `hypergraph/`, whose dependencies are listed in `hypergraph/package.json`.

### Install documentation-site dependencies

Use this when editing or building the Rspress documentation site:

```bash
corepack enable
pnpm install
pnpm run docs:dev
```

Build the static docs site with:

```bash
pnpm run docs:build
```

### Optional context artifact support

`llms-ctx.txt` generation is enabled by setting `ENABLE_CTX=1`. The source install already includes the `llms-txt` and `llm-ctx` packages declared in `pyproject.toml`; if you are debugging a minimal or custom environment, confirm they are installed before enabling context output:

```bash
python -m pip show llms-txt llm-ctx
```

## Environment file

Use one environment file: the root `.env` next to `pyproject.toml`.

Both runtimes use that same root environment:

- the Python CLI reads root `.env` through `AppConfig`
- HyperGraph inherits root `.env` when launched with `lmstxt --ui`
- HyperGraph also treats the repository root as its Next/Turbopack root, so direct UI runs should use the same root `.env`

Copy `.env.example` to `.env` at the repository root and put all local settings there: `LMSTUDIO_*`, GitHub token, artifact output, CLI flags, and `HYPERGRAPH_OPENAI_*` overrides.

## Configure LM Studio

### Load the CLI and start the server

```bash
npx lmstudio install-cli
lms server start --port 1234
```

The server must expose an OpenAI-compatible endpoint, commonly `http://localhost:1234/v1`.

### Ensure the target model is downloaded

Open LM Studio, download the model you want to use, and confirm its exact identifier appears in the **Server** tab. Set that identifier with `LMSTUDIO_MODEL` in `.env` or pass it with `--model`.

## Quick start

Run the CLI against any GitHub repository:

```bash
lmstxt https://github.com/owner/repo \
  --model "$LMSTUDIO_MODEL" \
  --api-base http://localhost:1234/v1 \
  --stamp
```

The command writes artifacts to `artifacts/owner/repo/`. Use `--output-dir` to override the destination.

To launch HyperGraph without generating artifacts:

```bash
lmstxt --ui
```

To generate graph artifacts and open them in HyperGraph automatically after generation:

```bash
lmstxt https://github.com/owner/repo \
  --generate-graph \
  --graph-only \
  --verbose-budget \
  --ui
```

The CLI will:
- start/reuse the HyperGraph UI server (default `http://localhost:3000`)
- auto-open the browser to HyperGraph, or to the generated graph when a repo graph is produced
- print the same handoff URL for manual reuse when loading a generated graph

To open HyperGraph directly to an existing graph artifact:

```bash
lmstxt --ui artifacts/<owner>/<repo>/graph/repo.graph.json
```

To generate graph artifacts from existing `llms.txt` or `llms-full.txt` markdown files:

```bash
lmstxt --graph-from artifacts/<owner>/<repo>/<repo>-llms.txt
lmstxt --graph-from artifacts/<owner>/<repo>/<repo>-llms-full.txt
```

Use `--ui-no-open` to skip auto-opening the browser.

To stop a HyperGraph UI background process that was started by `lmstxt --ui`:

```bash
lmstxt --ui-stop
```

`--ui-stop` only stops a tracked process recorded under `artifacts/.ui-logs/`; it refuses to kill manually started or untracked UI servers.

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
| `LMSTUDIO_MODEL` | Required LM Studio model identifier unless `--model` is passed |
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

Use the built-in HyperGraph UI to inspect and generate `repo.graph.json` artifacts. Install the UI dependencies first:

```bash
npm --prefix hypergraph install
```

Start the UI directly with:

```bash
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

The CLI `--ui` flag can be used by itself to auto-start/reuse the UI and open HyperGraph. When used with a repository plus `--generate-graph`, it opens the generated graph and prints a ready-to-open URL that pre-fills this path and auto-loads the graph. When used as `lmstxt --ui <repo.graph.json>`, it opens directly to that existing graph artifact.

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

- `docs/README.md` - documentation index and organization map.
- `docs/getting-started.md` - beginner onboarding and first commands.
- `docs/architecture.md` - system design, data flow, and extension points.
- `docs/standards.md` - discovered coding/runtime conventions and recommended consistency rules.
- `docs/patterns.md` - architectural/code patterns, integration seams, and hotspots.
- `docs/security/dependency-security-posture.md` - dependency security posture and controls.
- `docs/audits/dependency-audit.md` - dependency audit and pinning notes.
- `docs/decisions/2026-04-29-rollout-compatibility.md` - rollout compatibility decision and gates.
- `docs/audits/brownfield-documentation-review-checklist.md` - human validation checklist for brownfield documentation claims.
- `docs/publishing.md` - publishing and release workflow notes.
- `docs/mcp-inspector-payloads.md` - MCP Inspector payloads for tool verification.

## Verify your setup

```bash
source .venv/bin/activate
python -m pytest
```

Default pytest runs skip slow package-install smoke tests. Run the release-gate packaging smoke tests explicitly when validating built distributions:

```bash
python -m pytest --run-packaging -m packaging
```

Build the documentation site with Rspress:

```bash
pnpm run docs:build
```

Using uv:

```bash
source .venv/bin/activate
uv run --extra test pytest
```

For distribution validation, build artifacts first and then run:

```bash
uv run --extra test pytest --run-packaging -m packaging
```

All default tests should pass quickly, confirming URL validation, fallback handling, and MCP resource exposure. Packaging smoke tests remain available as a slower release gate.

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
