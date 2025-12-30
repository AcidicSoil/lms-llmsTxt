---
title: "LM Studio llms.txt Generator"
description: "Generate llms.txt, llms-full, and fallback artifacts for GitHub repositories using DSPy with LM Studio."
---

[![PyPI](https://img.shields.io/pypi/v/lms-llmsTxt.svg?include_prereleases&cacheSeconds=60&t=1)](https://pypi.org/project/lms-llmsTxt/)
[![Downloads](https://img.shields.io/pypi/dm/lms-llmsTxt.svg?cacheSeconds=300)](https://pypi.org/project/lms-llmsTxt/)
[![TestPyPI](https://img.shields.io/badge/TestPyPI-lms-llmsTxt-informational?cacheSeconds=300)](https://test.pypi.org/project/lms-llmsTxt/)
[![CI](https://github.com/AcidicSoil/lms-llmsTxt/actions/workflows/release.yml/badge.svg)](https://github.com/AcidicSoil/lms-llmsTxt/actions/workflows/release.yml)
[![Repo](https://img.shields.io/badge/GitHub-AcidicSoil%2Flms-llmsTxt-181717?logo=github)](https://github.com/AcidicSoil/lms-llmsTxt)

## Overview

Use this CLI-first toolkit to produce LLM-friendly documentation bundles (`llms.txt`, `llms-full.txt`, optional `llms-ctx.txt`, and fallback JSON) for any GitHub repository. The generator wraps DSPy analyzers, manages LM Studio model lifecycle with the official Python SDK, and guarantees output even when the primary language model cannot respond.

<Info>
The pipeline validates curated links, detects default branches automatically, and writes artifacts to `artifacts/<owner>/<repo>/`.
</Info>

## Prerequisites

- Python 3.10 or later
- LM Studio server available locally (Developer tab → **Start Server**) or the CLI (`lms server start --port 1234`)
- GitHub API token in `GITHUB_ACCESS_TOKEN` or `GH_TOKEN`
- Optional: [`llms_txt`](https://pypi.org/project/llms-txt/) when you want to produce `llms-ctx.txt`

<Warning>
Install dependencies inside a virtual environment to avoid PEP 668 “externally managed environment” errors.
</Warning>

## Install

<Steps>
  <Step title="Create a virtual environment">
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```
  </Step>
  <Step title="Install the package with developer extras">
    ```bash
    pip install -e .[dev]
    ```
    Installing the editable package exposes the `lmstudio-llmstxt` CLI and brings in the `lmstudio` Python SDK plus pytest.
  </Step>
</Steps>

<Tip>
Keep the virtual environment active while running the CLI or tests so the SDK-based unload logic can import `lmstudio`.
</Tip>

## Configure LM Studio

<Steps>
  <Step title="Load the CLI">
    ```bash
    npx lmstudio install-cli
    lms server start --port 1234
    ```
    The server must expose an OpenAI-compatible endpoint, commonly `http://localhost:1234/v1`.
  </Step>
  <Step title="Ensure the target model is downloaded">
    Open LM Studio, download the model (for example `qwen/qwen3-4b-2507`), and confirm it appears in the **Server** tab.
  </Step>
</Steps>

## Quick start

Run the CLI against any GitHub repository:

```bash
lmstudio-llmstxt https://github.com/owner/repo \
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

<Check>
The pipeline always writes `llms.txt` and `llms-full.txt`, even when the language model call fails.
</Check>

## How it works

1. **Collect repository material** – the GitHub client gathers the file tree, README, package files, repository visibility, and default branch.
2. **Prepare LM Studio** – the manager confirms the requested model is loaded, auto-loading if necessary.
3. **Generate documentation** – DSPy produces curated content; on LM failures the fallback serializer builds markdown and JSON directly.
4. **Assemble `llms-full`** – curated links are re-fetched via raw GitHub URLs for public repos or authenticated API calls for private ones, with validation to remove dead links.
5. **Unload models safely** – the workflow first uses the official `lmstudio` SDK (`model.unload()` or `list_loaded_models`), then falls back to HTTP and CLI unload requests.

## Project layout

- `src/lmstudiotxt_generator/` – configuration, GitHub utilities, DSPy analyzers, LM Studio helpers, fallback renderer, and artifact writers
- `tests/` – pytest coverage for analyzer buckets, LM Studio handshake/unload logic, and pipeline fallbacks
- `artifacts/` – sample outputs generated from previous runs

## Verify your setup

```bash
source .venv/bin/activate
python -m pytest
```
### Windows

```bash
source .venv/Scripts/activate
python -m pytest
```


All tests should pass, confirming URL validation, fallback handling, and SDK-first unload behaviour.

## Troubleshooting

<Warning>
If `pip install -e .[dev]` fails with build tool errors (`cmake` or `pyarrow`), install the missing system packages and retry the installation before running tests.
</Warning>

<Tip>
When `llms-full` surfaces `[fetch-error]`, verify the curated link uses the repository’s actual default branch (`master` vs `main`). The analyzer keeps only live URLs, but custom additions may need manual tweaks.
</Tip>

<Info>
Set `LMSTUDIO_MODEL` and `GITHUB_ACCESS_TOKEN` in your shell profile to avoid repeating flags during iterative runs.
</Info>
