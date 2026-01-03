import logging
import sys
import json
from typing import List, Optional
from mcp.server.fastmcp import FastMCP, Context
from pydantic import Field

from .config import settings
from .models import GenerateResult, ReadArtifactResult, ArtifactName
from .runs import RunStore
from .generator import safe_generate
from .artifacts import read_resource_text, read_artifact_chunk

# Configure logging to stderr to avoid interfering with JSON-RPC on stdout
logging.basicConfig(
    stream=sys.stderr, 
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("llmstxt_mcp")

# Initialize RunStore (singleton for the server instance)
run_store = RunStore()

@mcp.tool(
    name="llmstxt_generate",
    annotations={
        "title": "Generate Documentation Bundle",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True
    }
)
def generate(
    url: str = Field(..., description="The URL of the repository to process (e.g., https://github.com/owner/repo)"),
    output_dir: str = Field("./output", description="Local directory to store artifacts"),
    depth: int = Field(1, description="Depth for dependency/link crawling", ge=0, le=3),
    concurrency: int = Field(5, description="Number of concurrent requests for fetching", ge=1, le=20),
    skip_repo_check: bool = Field(False, description="Skip validation of repository existence"),
    cache_lm: bool = Field(True, description="Enable LM caching")
) -> str:
    """
    Analyzes a repository and generates documentation artifacts (llms.txt, llms-full.txt) optimized for LLM consumption.

    This tool triggers a DSPy-powered analysis pipeline that crawls the repository, 
    identifies key documentation, and synthesizes a curated index.

    Args:
        url (str): Repository URL.
        output_dir (str): Where to save files.
        depth (int): Crawl depth (default 1).
        concurrency (int): Parallel fetch limit (default 5).
        skip_repo_check (bool): If true, bypasses GH API existence check.
        cache_lm (bool): Use cached results for identical LLM prompts.

    Returns:
        str: JSON-formatted GenerateResult containing run_id and artifact references.
        
        Success Schema:
        {
            "run_id": "uuid-string",
            "status": "success",
            "artifacts": [
                {"name": "llms.txt", "path": "...", "size_bytes": 123, "hash_sha256": "..."}
            ]
        }
    """
    logger.info(f"Starting generation for {url}")
    result = safe_generate(
        run_store=run_store,
        url=url,
        output_dir=output_dir,
        depth=depth,
        concurrency=concurrency,
        skip_repo_check=skip_repo_check,
        cache_lm=cache_lm
    )
    return result.model_dump_json(indent=2)

@mcp.tool(
    name="llmstxt_list_runs",
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
        str: JSON list of GenerateResult objects.
    """
    runs = run_store.list_runs(limit=limit)
    return json.dumps([r.model_dump() for r in runs], indent=2)

@mcp.tool(
    name="llmstxt_read_artifact",
    annotations={
        "title": "Read Artifact Content",
        "readOnlyHint": True,
        "idempotentHint": True
    }
)
def read_artifact(
    run_id: str = Field(..., description="The UUID of the run"),
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
    content = read_artifact_chunk(run_store, run_id, artifact_name, offset, effective_limit)
    
    res = ReadArtifactResult(
        content=content,
        truncated=(len(content) == effective_limit),
        total_chars=len(content)
    )
    return res.model_dump_json(indent=2)

@mcp.resource("llmstxt://runs/{run_id}/{artifact_name}")
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

def main():
    """Entry point for the MCP server."""
    mcp.run()

if __name__ == "__main__":
    main()