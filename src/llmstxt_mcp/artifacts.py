from pathlib import Path
from .config import settings
from .runs import RunStore
from .hashing import read_text_preview

def resource_uri(run_id: str, artifact_name: str) -> str:
    """Generates a standardized URI for a run artifact."""
    return f"llmstxt://runs/{run_id}/{artifact_name}"

def read_resource_text(run_store: RunStore, run_id: str, artifact_name: str) -> str:
    """
    Reads text content from an artifact, truncated if necessary.
    Returns the content string (with truncation footer if applied).
    """
    run = run_store.get_run(run_id)
    # Find artifact by name
    artifact = next((a for a in run.artifacts if a.name == artifact_name), None)
    if not artifact:
        raise ValueError(f"Artifact {artifact_name} not found in run {run_id}")
    
    # Read content using hashing utility
    content, truncated = read_text_preview(
        Path(artifact.path), 
        settings.LLMSTXT_MCP_RESOURCE_MAX_CHARS
    )
    
    if truncated:
        content += "\n... (content truncated)"
        
    return content

def read_artifact_chunk(run_store: RunStore, run_id: str, artifact_name: str, offset: int, limit: int) -> str:
    """
    Reads a specific chunk of an artifact file.
    Returns the content string.
    """
    run = run_store.get_run(run_id)
    artifact = next((a for a in run.artifacts if a.name == artifact_name), None)
    if not artifact:
        raise ValueError(f"Artifact {artifact_name} not found in run {run_id}")
    
    path = Path(artifact.path)
    if not path.exists():
        raise FileNotFoundError(f"Artifact file not found at {path}")
        
    try:
        # Check size first to avoid unnecessary opens if offset is out of bounds
        file_size = path.stat().st_size
        if offset >= file_size:
            return ""
            
        with open(path, "r", encoding="utf-8") as f:
            f.seek(offset)
            return f.read(limit)
    except UnicodeDecodeError:
        return "<Binary or non-UTF-8 content>"

