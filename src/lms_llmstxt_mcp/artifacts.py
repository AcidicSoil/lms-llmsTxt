from pathlib import Path
from .config import settings
from .runs import RunStore
from .hashing import read_text_preview

def _status_message(status: str, error_message: str | None) -> str:
    if status in ("pending", "processing"):
        return "Processing..."
    if status == "failed":
        return f"Failed: {error_message or 'Unknown error'}"
    return ""

def resource_uri(run_id: str, artifact_name: str) -> str:
    """Generates a standardized URI for a run artifact."""
    return f"llmstxt://runs/{run_id}/{artifact_name}"

def artifact_resource_uri(relative_path: str) -> str:
    """Generates a standardized URI for a persistent artifact on disk."""
    return f"llmstxt://artifacts/{relative_path}"

def read_resource_text(run_store: RunStore, run_id: str, artifact_name: str) -> str:
    """
    Reads text content from an artifact, truncated if necessary.
    Returns the content string (with truncation footer if applied).
    """
    run = run_store.get_run(run_id)
    if run.status != "completed":
        return _status_message(run.status, run.error_message)
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
    if run.status != "completed":
        return _status_message(run.status, run.error_message)
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

def scan_artifacts() -> list[Path]:
    """
    Scans the allowed root directory for all .txt artifact files.
    Returns a list of Path objects relative to the allowed root.
    """
    root = settings.LLMSTXT_MCP_ALLOWED_ROOT
    if not root.exists():
        return []
    
    # Return relative paths so the API consumer gets "org/repo/llms.txt"
    # rglob finds all .txt files recursively
    return sorted([
        p.relative_to(root) 
        for p in root.rglob("*.txt") 
        if p.is_file()
    ])