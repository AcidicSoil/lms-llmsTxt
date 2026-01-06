---
title: "LM Studio llms.txt Generator"
description: "Generate llms.txt, llms-full, and fallback artifacts for GitHub repositories using DSPy with LM Studio."
---

[![PyPI](https://img.shields.io/pypi/v/lms-llmstxt)](https://pypi.org/project/lms-llmsTxt/) [![Downloads](https://img.shields.io/pypi/dm/lms-llmstxt)](https://pypi.org/project/lms-llmsTxt/) [![TestPyPI](https://img.shields.io/badge/TestPyPI-lms--llmsTxt-informational)](https://test.pypi.org/project/lms-llmsTxt/) [![CI](https://github.com/AcidicSoil/lms-llmsTxt/actions/workflows/release.yml/badge.svg?branch=main)](https://github.com/AcidicSoil/lms-llmsTxt/actions/workflows/release.yml) [![Repo](https://img.shields.io/badge/GitHub-AcidicSoil%2Flms--llmsTxt-181717?logo=github)](https://github.com/AcidicSoil/lms-llmsTxt)

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

### Install the package with developer extras

```bash
pip install -e '.[dev]'
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
- **Resources**:
  - **Run-specific**: `lmstxt://runs/{run_id}/{artifact_name}`
  - **Persistent Directory**: `lmstxt://artifacts/{filename}` (e.g., `lmstxt://artifacts/owner/repo/repo-llms.txt`)

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

## Verify your setup

```bash
source .venv/bin/activate
python -m pytest
```

All tests should pass, confirming URL validation, fallback handling, and MCP resource exposure.

## Troubleshooting

> [!WARNING]
> If `pip install -e .[dev]` fails with build tool errors, ensure `cmake` and necessary compilers are installed.

> [!TIP]
> If the MCP server times out during generation, check `lmstxt_list_runs` to see if the background task is still processing. The `lmstxt_generate_*` tools return immediately to avoid client timeouts.

### MCP Inspector

```bash
npx @modelcontextprotocol/inspector --config ./inspector.config.json --server lmstxt
```

Use the payloads in `docs/mcp-inspector-payloads.md` to verify specific tool behaviors.