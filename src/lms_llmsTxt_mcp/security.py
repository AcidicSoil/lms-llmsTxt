from pathlib import Path
from .config import settings
from .errors import OutputDirNotAllowedError

def validate_output_dir(path: Path) -> Path:
    """
    Validates that the path is within the allowed root.
    Returns the resolved absolute path.
    """
    try:
        # Resolve both paths to absolute
        resolved_path = path.resolve()
        # Ensure allowed root exists or at least resolves fully
        allowed_root = settings.LLMSTXT_MCP_ALLOWED_ROOT.resolve()
        
        # Check containment
        if not resolved_path.is_relative_to(allowed_root):
            raise OutputDirNotAllowedError(f"Path {path} is not within allowed root {allowed_root}")
            
        return resolved_path
    except (ValueError, RuntimeError) as e:
        raise OutputDirNotAllowedError(f"Invalid path: {e}")
