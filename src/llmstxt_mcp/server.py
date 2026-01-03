import logging
import sys
from typing import List, Optional
from mcp.server.fastmcp import FastMCP, Context
from pydantic import Field

from .config import settings
from .models import GenerateResult, ReadArtifactResult, ArtifactName
from .runs import RunStore
from .generator import safe_generate
from .artifacts import read_resource_text, read_artifact_chunk

# Configure logging to stderr to avoid interfering with JSON-RPC on stdout
logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("llmstxt-mcp")

# Initialize RunStore (singleton for the server instance)
run_store = RunStore()

@mcp.tool(
    name="llmstxt_generate",
    description="Generate llms.txt and related documentation artifacts from a repository URL.",
    annotations={"destructiveHint": False}
)
def generate(
    url: str = Field(..., description="The URL of the repository to process (e.g., https://github.com/owner/repo)"),
    output_dir: str = Field("./output", description="Local directory to store artifacts"),
    depth: int = Field(1, description="Depth for dependency/link crawling"),
    concurrency: int = Field(5, description="Number of concurrent requests for fetching"),
    skip_repo_check: bool = Field(False, description="Skip validation of repository existence"),
    cache_lm: bool = Field(True, description="Enable LM caching")
) -> GenerateResult:
    """
    Analyzes a repository and generates documentation artifacts optimized for LLM consumption.
    Returns metadata about the generated files.
    """
    logger.info(f"Starting generation for {url}")
    return safe_generate(
        run_store=run_store,
        url=url,
        output_dir=output_dir,
        depth=depth,
        concurrency=concurrency,
        skip_repo_check=skip_repo_check,
        cache_lm=cache_lm
    )

@mcp.tool(
    name="llmstxt_list_runs",
    description="List recent generation runs."
)
def list_runs(
    limit: int = Field(10, description="Maximum number of runs to return")
) -> List[GenerateResult]:
    """
    Returns a list of recent generation runs, ordered by newest first.
    """
    return run_store.list_runs(limit=limit)

@mcp.tool(
    name="llmstxt_read_artifact",
    description="Read a specific chunk of a generated artifact file."
)
def read_artifact(
    run_id: str = Field(..., description="The ID of the run"),
    artifact_name: ArtifactName = Field(..., description="Name of the artifact (e.g., 'llms.txt')"),
    offset: int = Field(0, description="Byte offset to start reading from"),
    limit: int = Field(..., description="Maximum number of characters to read")
) -> ReadArtifactResult:
    """
    Reads content from a specific artifact file with pagination support.
    Use this for large files (like llms-full.txt) to read in chunks.
    """
    effective_limit = min(limit, settings.LLMSTXT_MCP_RESOURCE_MAX_CHARS)
    
    content = read_artifact_chunk(run_store, run_id, artifact_name, offset, effective_limit)
    
    return ReadArtifactResult(
        content=content,
        truncated=(len(content) == effective_limit),
        total_chars=len(content)
    )

@mcp.resource("llmstxt://runs/{run_id}/{artifact_name}")
def get_run_artifact(run_id: str, artifact_name: str) -> str:
    """
    Access a generated artifact as a resource.
    Note: Large files will be truncated according to configuration.
    """
    try:
        return read_resource_text(run_store, run_id, artifact_name)
    except Exception as e:
        raise ValueError(f"Failed to read resource: {e}")

def main():
    """Entry point for the MCP server."""
    mcp.run()

if __name__ == "__main__":
    main()
