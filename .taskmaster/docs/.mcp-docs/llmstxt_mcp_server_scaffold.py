tree
.
├── pyproject.toml
├── requirements.txt
└── src
    └── llmstxt_mcp
        ├── __init__.py
        ├── models.py
        └── server.py


# path: pyproject.toml
```toml
[project]
name = "llmstxt-mcp"
version = "0.1.0"
description = "MCP server wrapper around lmstudiotxt_generator (llms.txt / llms-full.txt / llms-ctx.txt generator)"
readme = "README.md"  # TODO: create if you want publishing metadata
requires-python = ">=3.11"

# NOTE:
# - Dependencies are derived from imports in src.md and MCP SDK docs.
# - Pin/adjust versions to match your environment.
dependencies = [
  "mcp[cli]>=1.7.1",
  "pydantic>=2.0",
  "requests>=2.31",
  "lmstudio>=1.0.0",
  "litellm>=1.0.0",
  "dspy-ai>=3.0.0",
  "python-dotenv>=1.0.0",
  "llms-txt>=0.0.4",
]

[project.scripts]
llmstxt-mcp = "llmstxt_mcp.server:main"

[tool.setuptools]
package-dir = {"" = "src"}

[tool.setuptools.packages.find]
where = ["src"]

# TODO: If you already have a pyproject.toml, merge only the relevant bits above.
```


# path: requirements.txt
```txt
# MCP server runtime
mcp[cli]>=1.7.1
pydantic>=2.0

# generator runtime (derived from imports in src.md)
requests>=2.31
lmstudio>=1.0.0
litellm>=1.0.0
dspy-ai>=3.0.0
python-dotenv>=1.0.0
llms-txt>=0.0.4

# TODO: if your existing project pins versions, keep those pins.
```


# path: src/llmstxt_mcp/__init__.py
```python
"""MCP server wrapper around lmstudiotxt_generator.

Exports a single MCP server that can:
- generate llms.txt + llms-full.txt (+ optional llms-ctx.txt)
- expose generated artifacts via MCP resources and chunked reads
"""

from .server import mcp

__all__ = ["mcp"]
```


# path: src/llmstxt_mcp/models.py
```python
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


ArtifactName = Literal["llms.txt", "llms-full.txt", "llms-ctx.txt", "llms.json"]


class ArtifactRef(BaseModel):
    """Metadata for a generated artifact."""

    name: ArtifactName = Field(description="Artifact filename")
    uri: str = Field(description="MCP resource URI for reading the artifact")
    path: str = Field(description="Absolute path on the MCP server host")
    bytes: int = Field(description="File size in bytes")
    sha256: str = Field(description="SHA-256 of file contents")
    preview: Optional[str] = Field(
        default=None,
        description=(
            "Optional preview text included inline (typically truncated). "
            "Use llmstxt_read_artifact or the resource URI for full content."
        ),
    )
    truncated: bool = Field(
        default=False,
        description="True if preview was truncated to inline_max_chars",
    )


class GenerateResult(BaseModel):
    """Structured output for llmstxt_generate."""

    run_id: str = Field(description="Opaque ID referencing this generation run")
    repo_url: str = Field(description="Input GitHub repo URL")
    owner: str = Field(description="GitHub owner/org")
    repo: str = Field(description="GitHub repository name")
    output_root: str = Field(description="Output directory for this run")
    created_at: datetime = Field(description="UTC timestamp when run completed")
    artifacts: list[ArtifactRef] = Field(description="Generated artifacts")
    notes: list[str] = Field(default_factory=list, description="Non-fatal warnings")


class ReadArtifactResult(BaseModel):
    """Chunked artifact read result."""

    run_id: str
    artifact: ArtifactName
    offset: int = Field(description="Starting character offset used")
    limit: int = Field(description="Maximum characters requested")
    eof: bool = Field(description="True if end-of-file reached")
    text: str = Field(description="Returned text chunk")
```


# path: src/llmstxt_mcp/server.py
```python
from __future__ import annotations

import argparse
import asyncio
import hashlib
import logging
import os
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Literal, Optional

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from llmstxt_mcp.models import ArtifactName, ArtifactRef, GenerateResult, ReadArtifactResult

# The generator code from src.md (your existing library)
from lmstudiotxt_generator import AppConfig, LMStudioConnectivityError
from lmstudiotxt_generator.github import owner_repo_from_url
from lmstudiotxt_generator.pipeline import run_generation


# IMPORTANT: StdIO MCP servers must not write protocol-breaking output to stdout.
# Keep logs on stderr.
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger("llmstxt_mcp")


# Recommended for production Streamable HTTP: stateless_http + json_response
mcp = FastMCP(name="llmstxt", stateless_http=True, json_response=True)


@dataclass(frozen=True)
class RunRecord:
    created_at: datetime
    output_root: Path
    artifacts: dict[ArtifactName, Path]


_RUNS: dict[str, RunRecord] = {}
_GEN_LOCK = asyncio.Lock()  # avoid shared global LM/DSPy reconfiguration races


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_text_preview(path: Path, max_chars: int) -> tuple[str, bool]:
    text = path.read_text(encoding="utf-8", errors="replace")
    if max_chars <= 0 or len(text) <= max_chars:
        return text, False
    return text[:max_chars], True


def _validate_output_dir(output_dir: Optional[str]) -> Optional[Path]:
    """Prevent writing outside an allowlisted root.

    Default allowed root is the current working directory.
    Override with env: LLMSTXT_MCP_ALLOWED_ROOT
    """

    if output_dir is None:
        return None

    allowed_root = Path(os.getenv("LLMSTXT_MCP_ALLOWED_ROOT", os.getcwd())).resolve()
    out = Path(output_dir).expanduser().resolve()

    try:
        out.relative_to(allowed_root)
    except ValueError as e:
        raise ValueError(
            f"Refusing output_dir outside allowed root. "
            f"output_dir={str(out)!r} allowed_root={str(allowed_root)!r}"
        ) from e

    return out


def _resource_uri(run_id: str, artifact: ArtifactName) -> str:
    return f"llmstxt://runs/{run_id}/{artifact}"


@mcp.tool()
async def llmstxt_generate(
    repo_url: Annotated[
        str,
        Field(description="GitHub repo URL (https://github.com/<owner>/<repo> or git@github.com:<owner>/<repo>.git)"),
    ],
    enable_ctx: Annotated[
        bool,
        Field(description="If true, also attempt to generate llms-ctx.txt (requires llms-txt to be installed)."),
    ] = False,
    link_style: Annotated[
        Literal["blob", "raw"],
        Field(description="How to build links in llms.txt: 'blob' (GitHub UI) or 'raw' (raw.githubusercontent.com)."),
    ] = "blob",
    output_dir: Annotated[
        Optional[str],
        Field(
            default=None,
            description=(
                "Base output directory root. A per-repo subfolder is created under this. "
                "If omitted, the generator's default is used."
            ),
        ),
    ] = None,
    github_token: Annotated[
        Optional[str],
        Field(description="Optional GitHub token for higher rate limits / private repos."),
    ] = None,
    model: Annotated[
        Optional[str],
        Field(description="Optional LM Studio model identifier override."),
    ] = None,
    api_base: Annotated[
        Optional[str],
        Field(description="Optional LM Studio API base override (e.g., http://localhost:1234/v1)."),
    ] = None,
    api_key: Annotated[
        Optional[str],
        Field(description="Optional API key override (LM Studio typically ignores this)."),
    ] = None,
    stamp: Annotated[
        bool,
        Field(description="If true, add a small 'generated by' stamp header in the output."),
    ] = False,
    cache_lm: Annotated[
        bool,
        Field(description="If true, keep LM Studio model loaded across calls (lower latency, higher VRAM/RAM usage)."),
    ] = False,
    inline_max_chars: Annotated[
        int,
        Field(description="Max characters to inline as preview per artifact in the tool response.")
    ] = 4000,
) -> GenerateResult:
    """Generate llms.txt (+ llms-full.txt, optional llms-ctx.txt) for a GitHub repository.

    Returns:
    - Structured metadata for generated artifacts
    - MCP resource URIs for retrieving full file contents

    Notes:
    - This tool writes files to disk on the MCP server host.
    - Use llmstxt_read_artifact (chunked) or the provided resource URIs to fetch full contents.
    """

    # validate repo URL early
    owner, repo = owner_repo_from_url(repo_url)

    out_dir = _validate_output_dir(output_dir)

    cfg = AppConfig()
    cfg.github_token = github_token or cfg.github_token
    cfg.link_style = link_style
    cfg.enable_ctx = bool(enable_ctx)

    if out_dir is not None:
        cfg.output_dir = out_dir

    # LM Studio overrides (optional)
    if model:
        cfg.model = model
    if api_base:
        cfg.api_base = api_base
    if api_key:
        cfg.api_key = api_key

    run_id = uuid.uuid4().hex
    notes: list[str] = []

    async with _GEN_LOCK:
        try:
            artifacts = await asyncio.to_thread(
                run_generation,
                repo_url,
                cfg,
                stamp,
                cache_lm,
            )
        except LMStudioConnectivityError as e:
            # Raise a clear error; clients surface tool errors to the user.
            raise RuntimeError(
                "LM Studio is not reachable. Ensure LM Studio is running with the local server enabled "
                "(and api_base/model are correct)."
            ) from e

    # Build artifact list
    produced: dict[ArtifactName, Path] = {
        "llms.txt": Path(artifacts.llms_path),
        "llms-full.txt": Path(artifacts.llms_full_path),
    }

    if artifacts.llms_ctx_path:
        produced["llms-ctx.txt"] = Path(artifacts.llms_ctx_path)
    elif enable_ctx:
        notes.append("enable_ctx=true but llms-ctx.txt was not generated (is 'llms-txt' installed?)")

    if artifacts.json_path:
        produced["llms.json"] = Path(artifacts.json_path)

    # Store run record for later reads
    created_at = datetime.now(timezone.utc)
    _RUNS[run_id] = RunRecord(
        created_at=created_at,
        output_root=Path(artifacts.output_root),
        artifacts=produced,
    )

    refs: list[ArtifactRef] = []
    for name, path in produced.items():
        stat = path.stat()
        preview, truncated = _read_text_preview(path, inline_max_chars)
        refs.append(
            ArtifactRef(
                name=name,
                uri=_resource_uri(run_id, name),
                path=str(path.resolve()),
                bytes=stat.st_size,
                sha256=_sha256_file(path),
                preview=preview,
                truncated=truncated,
            )
        )

    return GenerateResult(
        run_id=run_id,
        repo_url=repo_url,
        owner=owner,
        repo=repo,
        output_root=str(Path(artifacts.output_root).resolve()),
        created_at=created_at,
        artifacts=refs,
        notes=notes,
    )


@mcp.tool()
def llmstxt_list_runs(
    limit: Annotated[int, Field(description="Maximum number of runs to return.")] = 20,
) -> dict[str, object]:
    """List recent runs currently held in memory by this MCP server."""

    items = sorted(_RUNS.items(), key=lambda kv: kv[1].created_at, reverse=True)[: max(limit, 0)]
    return {
        "count": len(items),
        "runs": [
            {
                "run_id": run_id,
                "created_at": rec.created_at.isoformat(),
                "output_root": str(rec.output_root),
                "artifacts": {k: _resource_uri(run_id, k) for k in rec.artifacts.keys()},
            }
            for run_id, rec in items
        ],
    }


@mcp.tool()
def llmstxt_read_artifact(
    run_id: Annotated[str, Field(description="Run ID returned by llmstxt_generate")],
    artifact: Annotated[ArtifactName, Field(description="Artifact filename")],
    offset: Annotated[int, Field(description="Character offset (0-based)")] = 0,
    limit: Annotated[int, Field(description="Maximum characters to return")] = 20000,
) -> ReadArtifactResult:
    """Read a chunk from a generated artifact (safe for large llms-full.txt files)."""

    rec = _RUNS.get(run_id)
    if rec is None:
        raise ValueError(f"Unknown run_id: {run_id}")

    path = rec.artifacts.get(artifact)
    if path is None:
        raise ValueError(f"Artifact not found for run {run_id}: {artifact}")

    text = path.read_text(encoding="utf-8", errors="replace")

    offset = max(offset, 0)
    limit = max(limit, 0)

    chunk = text[offset : offset + limit]
    eof = (offset + limit) >= len(text)

    return ReadArtifactResult(
        run_id=run_id,
        artifact=artifact,
        offset=offset,
        limit=limit,
        eof=eof,
        text=chunk,
    )


@mcp.resource("llmstxt://runs/{run_id}/{artifact}")
def llmstxt_resource(run_id: str, artifact: str) -> str:
    """Read a generated artifact via an MCP Resource URI.

    The server caps resource reads to avoid accidentally dumping multi-megabyte llms-full.txt files
    into a single context load. Use llmstxt_read_artifact for chunked reads.
    """

    rec = _RUNS.get(run_id)
    if rec is None:
        return f"Unknown run_id: {run_id}"

    if artifact not in rec.artifacts:
        return f"Artifact not found for run {run_id}: {artifact}"

    max_chars = int(os.getenv("LLMSTXT_MCP_RESOURCE_MAX_CHARS", "200000"))
    text = rec.artifacts[artifact].read_text(encoding="utf-8", errors="replace")

    if max_chars > 0 and len(text) > max_chars:
        return (
            "[TRUNCATED RESOURCE]\n"
            f"Full length: {len(text)} chars. Use llmstxt_read_artifact(run_id, artifact, offset, limit) for chunked reads.\n\n"
            + text[:max_chars]
        )

    return text


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Run the llmstxt MCP server")
    p.add_argument(
        "--transport",
        default=os.getenv("MCP_TRANSPORT", "stdio"),
        choices=["stdio", "streamable-http"],
        help="Transport to run (default: stdio).",
    )
    return p


def main(argv: Optional[list[str]] = None) -> None:
    args = build_arg_parser().parse_args(argv)

    # stdio is the most widely supported transport; streamable-http is recommended for production.
    # (See MCP docs for transport details.)
    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
