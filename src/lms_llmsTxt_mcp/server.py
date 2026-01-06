import json
import logging
import sys
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .config import settings
from .models import ReadArtifactResult, ArtifactName, RunRecord, ArtifactMetadata
from .runs import RunStore
from .generator import (
    safe_generate_llms_txt,
    safe_generate_llms_full,
    safe_generate_llms_ctx,
)
from .artifacts import (
    read_resource_text, 
    read_artifact_chunk, 
    scan_artifacts, 
    artifact_resource_uri
)
from .security import validate_output_dir
from .hashing import read_text_preview
from lms_llmsTxt.github import owner_repo_from_url

# Configure logging to stderr to avoid interfering with JSON-RPC on stdout
logging.basicConfig(
    stream=sys.stderr, 
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("lms-llmsTxt")

# Initialize RunStore (singleton for the server instance)
run_store = RunStore(
    max_runs=settings.LLMSTXT_MCP_RUN_MAX,
    ttl_seconds=settings.LLMSTXT_MCP_RUN_TTL_SECONDS,
    cleanup_interval_seconds=settings.LLMSTXT_MCP_RUN_CLEANUP_INTERVAL_SECONDS,
)
run_store.start_cleanup_worker()

def _spawn_background(target, *args, **kwargs) -> None: 
    def _runner() -> None: 
        try:
            target(*args, **kwargs)
        except Exception:
            logger.exception("Background job failed")

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()

def _start_run(run_id: str | None) -> str:
    if run_id:
        run_store.get_run(run_id)
        run_store.update_run(run_id, status="processing", error_message=None)
        return run_id
    new_run_id = str(uuid.uuid4())
    run_store.put_run(RunRecord(run_id=new_run_id, status="processing"))
    return new_run_id


def _artifact_path_from_url(output_dir: Path, repo_url: str, artifact_name: str) -> Path:
    owner, repo = owner_repo_from_url(repo_url)
    base_name = repo.lower().replace(" ", "-")
    suffix_map = {
        "llms.txt": "llms.txt",
        "llms-full.txt": "llms-full.txt",
        "llms-ctx.txt": "llms-ctx.txt",
        "llms.json": "llms.json",
    }
    suffix = suffix_map.get(artifact_name, artifact_name)
    return output_dir / owner / repo / f"{base_name}-{suffix}"


def _read_file_chunk(path: Path, offset: int, limit: int) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Artifact file not found at {path}")
    try:
        file_size = path.stat().st_size
        if offset >= file_size:
            return ""
        with open(path, "r", encoding="utf-8") as f:
            f.seek(offset)
            return f.read(limit)
    except UnicodeDecodeError:
        return "<Binary or non-UTF-8 content>"

@mcp.tool(
    name="lmstxt_generate_llms_txt",
    annotations={
        "title": "Generate llms.txt",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True
    }
)
def generate_llms_txt(
    url: str = Field(..., description="The URL of the repository to process (e.g., https://github.com/owner/repo)"),
    output_dir: str = Field("./artifacts", description="Local directory to store artifacts"),
    cache_lm: bool = Field(True, description="Enable LM caching")
) -> str:
    """
    Generates llms.txt (and llms.json on fallback) for a repository.

    Returns:
        str: JSON-formatted RunRecord containing run_id and status.
    """
    logger.info("Queueing llms.txt generation for %s", url)
    validate_output_dir(Path(output_dir))
    run_id = _start_run(None)
    _spawn_background(
        safe_generate_llms_txt,
        run_store,
        run_id,
        url,
        output_dir,
        cache_lm,
    )
    return run_store.get_run(run_id).model_dump_json(indent=2)


@mcp.tool(
    name="lmstxt_generate_llms_full",
    annotations={
        "title": "Generate llms-full.txt",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True
    }
)
def generate_llms_full(
    repo_url: str = Field(..., description="Repository URL for resolving default branch and access"),
    run_id: str | None = Field(None, description="Run ID containing llms.txt (optional)"),
    output_dir: str = Field("./artifacts", description="Output directory root (used when run_id is omitted)"),
) -> str:
    """
    Generates llms-full.txt from an existing llms.txt artifact.

    Returns:
        str: JSON-formatted RunRecord with updated artifacts.
    """
    logger.info("Queueing llms-full generation for %s", run_id)
    if not run_id:
        validate_output_dir(Path(output_dir))
    effective_run_id = _start_run(run_id)
    _spawn_background(
        safe_generate_llms_full,
        run_store,
        effective_run_id,
        repo_url,
        output_dir,
    )
    return run_store.get_run(effective_run_id).model_dump_json(indent=2)


@mcp.tool(
    name="lmstxt_generate_llms_ctx",
    annotations={
        "title": "Generate llms-ctx.txt",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True
    }
)
def generate_llms_ctx(
    run_id: str | None = Field(None, description="Run ID containing llms.txt (optional)"),
    repo_url: str | None = Field(None, description="Repository URL (required when run_id is omitted)"),
    output_dir: str = Field("./artifacts", description="Output directory root (used when run_id is omitted)"),
) -> str:
    """
    Generates llms-ctx.txt from an existing llms.txt artifact.

    Returns:
        str: JSON-formatted RunRecord with updated artifacts.
    """
    logger.info("Queueing llms-ctx generation for %s", run_id)
    if not run_id:
        if not repo_url:
            raise ValueError("repo_url is required when run_id is omitted")
        validate_output_dir(Path(output_dir))
    effective_run_id = _start_run(run_id)
    _spawn_background(
        safe_generate_llms_ctx,
        run_store,
        effective_run_id,
        repo_url,
        output_dir,
    )
    return run_store.get_run(effective_run_id).model_dump_json(indent=2)

@mcp.tool(
    name="lmstxt_list_runs",
    annotations={
        "title": "List Generation History",
        "readOnlyHint": True,
        "idempotentHint": True
    }
)
def list_runs(
    limit: int = Field(10, description="Maximum number of runs to return", ge=1, le=50)
) -> str:
    """
    Returns a list of recent generation runs, ordered by newest first.

    Returns:
        str: JSON list of RunRecord objects.
    """
    runs = run_store.list_runs(limit=limit)
    return json.dumps([r.model_dump(mode="json") for r in runs], indent=2)

@mcp.tool(
    name="lmstxt_list_all_artifacts",
    annotations={
        "title": "List All Persistent Artifacts",
        "readOnlyHint": True,
        "idempotentHint": True
    }
)
def list_all_artifacts() -> str:
    """
    Returns a list of all .txt artifact files found in the persistent artifacts directory.
    This includes files from previous server sessions.
    """
    paths = scan_artifacts()
    root = settings.LLMSTXT_MCP_ALLOWED_ROOT
    results = []
    for p in paths:
        full_path = root / p
        stats = full_path.stat()
        results.append(ArtifactMetadata(
            filename=str(p),
            size_bytes=stats.st_size,
            last_modified=datetime.fromtimestamp(stats.st_mtime, tz=timezone.utc),
            uri=artifact_resource_uri(str(p))
        ))
    return json.dumps([r.model_dump(mode="json") for r in results], indent=2)

@mcp.tool(
    name="lmstxt_read_artifact",
    annotations={
        "title": "Read Artifact Content",
        "readOnlyHint": True,
        "idempotentHint": True
    }
)
def read_artifact(
    run_id: str | None = Field(None, description="The UUID of the run (optional)"),
    repo_url: str | None = Field(None, description="Repository URL (required when run_id is omitted)"),
    output_dir: str = Field("./artifacts", description="Output directory root (used when run_id is omitted)"),
    artifact_name: ArtifactName = Field(..., description="Name of the artifact (e.g., 'llms.txt', 'llms-full.txt')"),
    offset: int = Field(0, description="Byte offset to start reading from", ge=0),
    limit: int = Field(10000, description="Maximum number of characters to read", ge=1, le=100000)
) -> str:
    """
    Reads content from a specific artifact file with pagination support.
    
    Use this for large files (like llms-full.txt) to read in manageable chunks.

    Args:
        run_id (str): Run identifier.
        artifact_name (str): One of: llms.txt, llms-full.txt, llms-ctx.txt, llms.json.
        offset (int): Starting position.
        limit (int): Max characters to return.

    Returns:
        str: JSON-formatted ReadArtifactResult.
        
        Schema:
        {
            "content": "file text content...",
            "truncated": bool,
            "total_chars": int
        }
    """
    effective_limit = min(limit, settings.LLMSTXT_MCP_RESOURCE_MAX_CHARS)
    if run_id:
        logger.info("Reading artifact via run_id %s", run_id)
        content = read_artifact_chunk(run_store, run_id, artifact_name, offset, effective_limit)
    else:
        if not repo_url:
            raise ValueError("repo_url is required when run_id is omitted")
        logger.info("Reading artifact via repo_url + output_dir")
        validated_dir = validate_output_dir(Path(output_dir))
        artifact_path = _artifact_path_from_url(validated_dir, repo_url, artifact_name)
        content = _read_file_chunk(artifact_path, offset, effective_limit)
    
    res = ReadArtifactResult(
        content=content,
        truncated=(len(content) == effective_limit),
        total_chars=len(content)
    )
    return res.model_dump_json(indent=2)

@mcp.resource("lmstxt://runs/{run_id}/{artifact_name}")
def get_run_artifact(run_id: str, artifact_name: str) -> str:
    """
    Access a generated artifact as a static resource.
    
    Note: Large files will be truncated according to the server's 
    LLMSTXT_MCP_RESOURCE_MAX_CHARS configuration.
    """
    try:
        return read_resource_text(run_store, run_id, artifact_name)
    except Exception as e:
        logger.error(f"Resource access failed: {e}")
        raise ValueError(f"Failed to read resource: {e}")

@mcp.resource("lmstxt://artifacts/{filename}")
def get_persistent_artifact(filename: str) -> str:
    """
    Access a persistent artifact on disk as a resource.
    
    Note: Large files will be truncated according to the server's 
    LLMSTXT_MCP_RESOURCE_MAX_CHARS configuration.
    """
    root = settings.LLMSTXT_MCP_ALLOWED_ROOT
    path = root / filename
    
    # Security: ensure path is within root
    validate_output_dir(path.parent)
    
    if not path.exists():
        raise FileNotFoundError(f"Artifact {filename} not found")
        
    content, truncated = read_text_preview(
        path, 
        settings.LLMSTXT_MCP_RESOURCE_MAX_CHARS
    )
    
    if truncated:
        content += "\n... (content truncated)"
        
    return content

def main():
    """Entry point for the MCP server."""
    mcp.run()

if __name__ == "__main__":
    main()