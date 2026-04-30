import hashlib
from pathlib import Path

def sha256_file(path: Path) -> str:
    """Calculates the SHA256 hash of a file efficiently."""
    sha256_hash = hashlib.sha256()
    with open(path, "rb") as f:
        # Read in 4KB chunks
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def read_text_preview(path: Path, max_chars: int) -> tuple[str, bool]:
    """
    Reads up to max_chars from a text file.
    Returns (content, is_truncated).
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read(max_chars + 1)
            if len(content) > max_chars:
                return content[:max_chars], True
            return content, False
    except UnicodeDecodeError:
        # Handle cases where the file isn't valid UTF-8
        return "<Binary or non-UTF-8 content>", True
