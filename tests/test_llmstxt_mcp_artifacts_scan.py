import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch
import pytest
from lms_llmstxt_mcp import artifacts
from lms_llmstxt_mcp.config import Settings

@pytest.fixture
def temp_output_dir():
    # Create a temp directory
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    # Cleanup
    shutil.rmtree(temp_dir)

def test_scan_artifacts(temp_output_dir):
    # Setup: Create dummy structure
    # output/
    #   org1/
    #     repo1/
    #       llms.txt
    #       other.json
    #   org2/
    #     repo2/
    #       llms-full.txt
    
    (temp_output_dir / "org1" / "repo1").mkdir(parents=True)
    (temp_output_dir / "org2" / "repo2").mkdir(parents=True)
    
    (temp_output_dir / "org1" / "repo1" / "llms.txt").write_text("content")
    (temp_output_dir / "org1" / "repo1" / "other.json").write_text("{}")
    (temp_output_dir / "org2" / "repo2" / "llms-full.txt").write_text("full content")
    
    # Override settings to point to temp_output_dir
    with patch("lms_llmstxt_mcp.artifacts.settings", Settings(LLMSTXT_MCP_ALLOWED_ROOT=temp_output_dir)):
        files = artifacts.scan_artifacts()
        
        # Verify
        assert len(files) == 2
        # Paths should be relative
        assert Path("org1/repo1/llms.txt") in files
        assert Path("org2/repo2/llms-full.txt") in files
        assert Path("org1/repo1/other.json") not in files

def test_scan_artifacts_non_existent_root():
    # If root doesn't exist, should return empty list
    with patch("lms_llmstxt_mcp.artifacts.settings", Settings(LLMSTXT_MCP_ALLOWED_ROOT=Path("/non/existent/path"))):
        assert artifacts.scan_artifacts() == []
