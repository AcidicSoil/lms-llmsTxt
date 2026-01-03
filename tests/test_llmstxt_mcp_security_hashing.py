import pytest
from pathlib import Path
from llmstxt_mcp.security import validate_output_dir
from llmstxt_mcp.hashing import sha256_file, read_text_preview
from llmstxt_mcp.errors import OutputDirNotAllowedError
from llmstxt_mcp.config import settings

def test_validate_output_dir(tmp_path):
    # Override settings to use tmp_path as the allowed root
    settings.LLMSTXT_MCP_ALLOWED_ROOT = tmp_path
    
    # Create a valid subdirectory
    valid = tmp_path / "subdir"
    valid.mkdir()
    
    # Should pass
    assert validate_output_dir(valid) == valid.resolve()
    
    # Should fail (absolute path outside)
    with pytest.raises(OutputDirNotAllowedError):
        validate_output_dir(Path("/etc/passwd"))
        
    # Should fail (traversal)
    # resolve() handles '..' so this effectively checks against the parent
    with pytest.raises(OutputDirNotAllowedError):
        validate_output_dir(tmp_path / "..")

def test_hashing(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("hello world", encoding="utf-8")
    
    # Verified SHA256 of "hello world"
    expected = "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
    assert sha256_file(f) == expected

def test_read_preview(tmp_path):
    f = tmp_path / "long.txt"
    f.write_text("1234567890", encoding="utf-8")
    
    # Truncated
    content, truncated = read_text_preview(f, 5)
    assert content == "12345"
    assert truncated is True
    
    # Exact match
    content, truncated = read_text_preview(f, 10)
    assert content == "1234567890"
    assert truncated is False
    
    # More than enough
    content, truncated = read_text_preview(f, 20)
    assert content == "1234567890"
    assert truncated is False
