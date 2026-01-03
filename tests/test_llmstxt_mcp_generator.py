import threading
import time
import pytest
from unittest.mock import patch, MagicMock
from llmstxt_mcp.generator import safe_generate
from llmstxt_mcp.errors import LMStudioUnavailableError
from llmstxt_mcp.runs import RunStore
from lmstudiotxt_generator import LMStudioConnectivityError
from lmstudiotxt_generator.models import GenerationArtifacts

@pytest.fixture
def run_store():
    return RunStore()

def test_safe_generate_success(run_store, tmp_path):
    # Setup mock artifacts
    f1 = tmp_path / "llms.txt"
    f1.write_text("content")
    
    mock_artifacts = GenerationArtifacts(
        llms_txt_path=str(f1),
        llms_full_path="",
        ctx_path="",
        json_path="",
        used_fallback=False
    )
    
    with patch("llmstxt_mcp.generator.run_generation", return_value=mock_artifacts):
        result = safe_generate(run_store, "https://github.com/foo/bar")
        
        assert result.status == "success"
        assert len(result.artifacts) == 1
        assert result.artifacts[0].name == "llms.txt"
        assert result.artifacts[0].hash_sha256 is not None
        
        # Verify store update
        stored = run_store.get_run(result.run_id)
        assert stored == result

def test_safe_generate_failure(run_store):
    with patch("llmstxt_mcp.generator.run_generation") as mock_run:
        mock_run.side_effect = ValueError("Boom")
        
        with pytest.raises(RuntimeError):
            safe_generate(run_store, "https://github.com/foo/bar")
            
        # Verify failed run is stored (we can get the ID from the mock call or by listing)
        runs = run_store.list_runs()
        assert len(runs) == 1
        assert runs[0].status == "failed"
        assert "Boom" in runs[0].error_message