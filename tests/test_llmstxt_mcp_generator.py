import pytest
from unittest.mock import patch
from pathlib import Path
from llmstxt_mcp.generator import safe_generate_llms_txt
from llmstxt_mcp.errors import OutputDirNotAllowedError
from llmstxt_mcp.runs import RunStore
from llmstxt_mcp.models import RunRecord
from llmstxt_mcp.config import settings
from lmstudiotxt_generator.models import GenerationArtifacts

@pytest.fixture
def run_store():
    return RunStore()

def test_safe_generate_llms_txt_success(run_store, tmp_path):
    # Setup mock artifacts
    f1 = tmp_path / "llms.txt"
    f1.write_text("content")

    # Configure allowed root
    settings.LLMSTXT_MCP_ALLOWED_ROOT = tmp_path

    mock_artifacts = GenerationArtifacts(
        llms_txt_path=str(f1),
        llms_full_path=None,
        ctx_path=None,
        json_path=None,
        used_fallback=False
    )

    with patch("llmstxt_mcp.generator.run_generation", return_value=mock_artifacts):
        # Pass run_id=None to generate a new one
        result = safe_generate_llms_txt(
            run_store=run_store,
            run_id=None,
            url="https://github.com/foo/bar",
            output_dir=str(tmp_path)
        )
        
        assert result.status == "completed"
        assert len(result.artifacts) == 1
        assert result.artifacts[0].name == "llms.txt"

def test_safe_generate_llms_txt_security_violation(run_store, tmp_path):
    # Configure allowed root
    settings.LLMSTXT_MCP_ALLOWED_ROOT = tmp_path

    # Attempt to use a directory outside the root
    with pytest.raises(OutputDirNotAllowedError):
        safe_generate_llms_txt(
            run_store=run_store,
            run_id=None,
            url="https://github.com/foo/bar",
            output_dir="/etc"
        )

def test_safe_generate_llms_txt_failure(run_store, tmp_path):
    # Configure allowed root
    settings.LLMSTXT_MCP_ALLOWED_ROOT = tmp_path

    with patch("llmstxt_mcp.generator.run_generation") as mock_run:
        mock_run.side_effect = ValueError("Boom")

        with pytest.raises(RuntimeError):
            safe_generate_llms_txt(
                run_store=run_store,
                run_id=None,
                url="https://github.com/foo/bar",
                output_dir=str(tmp_path)
            )
        
        # Verify failed run is stored
        runs = run_store.list_runs()
        assert len(runs) == 1
        assert runs[0].status == "failed"
        assert "Boom" in runs[0].error_message