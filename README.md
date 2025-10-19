# LM Studio llms.txt Generator

This project scaffolds a reusable codebase for generating `llms.txt` documentation
with [DSPy](https://github.com/stanfordnlp/dspy) while targeting
[LM Studio](https://lmstudio.ai/)'s OpenAI-compatible API. It is inspired by the
DSPy tutorials but reorganized into a structured Python package ready for
automation or CLI usage.

## Prerequisites

- Python 3.10 or newer.
- LM Studio running the HTTP server (Developer tab → *Start Server*) or the CLI:

  ```bash
  npx lmstudio install-cli
  lms server start --port 1234
  ```

- A GitHub API token (`GITHUB_ACCESS_TOKEN` or `GH_TOKEN`) to fetch repository
  trees and file contents.

Optional:

- `llms_txt` package if you want to emit context files (`pip install llms-txt`).
- Set `ENABLE_CTX=1` to opt-in to context generation.

## Installation

```bash
pip install -e .
```

The editable install exposes the `lmstudio-llmstxt` CLI entry point.

## Usage

```bash
lmstudio-llmstxt https://github.com/owner/repo \
  --model qwen3-4b-instruct-2507@q6_k_xl \
  --api-base http://localhost:1234/v1 \
  --stamp
```

Artifacts are stored inside `./artifacts/<owner>/<repo>/` by default. Override
the target directory with `--output-dir`.

Environment variables can be used instead of flags:

- `LMSTUDIO_MODEL`
- `LMSTUDIO_BASE_URL`
- `LMSTUDIO_API_KEY`
- `OUTPUT_DIR`

## Project Structure

- `src/lmstudiotxt_generator/` contains reusable modules for configuration,
  GitHub data collection, DSPy analysis, and artifact generation.
- `pyproject.toml` defines package metadata and dependencies.
- `dspy_workspace/` keeps the original tutorial reference materials untouched.
- If LM Studio declines the structured request, the pipeline emits
  `*-llms.json` alongside the markdown so downstream tooling can rely on the
  bundled JSON Schema.

## Development Notes

- The DSPy `RepositoryAnalyzer` module mirrors the tutorial logic but is bundled
  as a reusable package component.
- LM Studio interactions use the OpenAI protocol, so the same prompts can run
  locally or against hosted APIs by adjusting environment variables.
- A lightweight pytest suite covers the LM Studio handshake and fallback
  behaviour.
- When the language model responds with a `BadRequestError` (for example if the
  model is not loaded or does not support JSON schema), the CLI falls back to a
  heuristic generator that serializes data using `LLMS_JSON_SCHEMA` before
  rendering markdown.
- The tooling will attempt to auto-load `LMSTUDIO_MODEL` via LM Studio's REST
  `/v1/models` endpoint before issuing any DSPy calls and report if the request
  fails.

### Running tests

Install the dev extras and execute the test suite:

```bash
pip install -e .[dev]
pytest
```
