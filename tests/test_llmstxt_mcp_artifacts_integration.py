import json
from pathlib import Path
import pytest
from lms_llmstxt_mcp.server import mcp, run_store, list_all_artifacts, get_persistent_artifact
from lms_llmstxt_mcp.config import settings
from unittest.mock import patch

@pytest.fixture
def mock_artifacts_dir(tmp_path):
    # Create dummy artifacts
    (tmp_path / "org1" / "repo1").mkdir(parents=True)
    (tmp_path / "org1" / "repo1" / "llms.txt").write_text("Hello Artifact")
    return tmp_path

def test_list_all_artifacts_tool(mock_artifacts_dir):
    with patch("lms_llmstxt_mcp.artifacts.settings.LLMSTXT_MCP_ALLOWED_ROOT", mock_artifacts_dir):
        with patch("lms_llmstxt_mcp.server.settings.LLMSTXT_MCP_ALLOWED_ROOT", mock_artifacts_dir):
            # Call the tool function directly
            result_json = list_all_artifacts()
            result = json.loads(result_json)
            
            assert len(result) == 1
            assert result[0]["filename"] == "org1/repo1/llms.txt"
            assert result[0]["uri"] == "llmstxt://artifacts/org1/repo1/llms.txt"

def test_get_persistent_artifact_resource(mock_artifacts_dir):
    with patch("lms_llmstxt_mcp.server.settings.LLMSTXT_MCP_ALLOWED_ROOT", mock_artifacts_dir):
        content = get_persistent_artifact("org1/repo1/llms.txt")
        assert content == "Hello Artifact"

def test_get_persistent_artifact_security(mock_artifacts_dir):
    with patch("lms_llmstxt_mcp.server.settings.LLMSTXT_MCP_ALLOWED_ROOT", mock_artifacts_dir):
        from lms_llmstxt_mcp.errors import OutputDirNotAllowedError
        
        with pytest.raises(OutputDirNotAllowedError):
            # Attempt path traversal
            get_persistent_artifact("../outside.txt")