from unittest.mock import patch
import pytest
from lms_llmstxt_mcp.generator import safe_generate_llms_txt
from lms_llmstxt_mcp.runs import RunStore
from lms_llmstxt.pipeline import run_generation

def test_safe_generate_llms_txt_calls_run_generation_with_correct_signature():
    """
    Ensures safe_generate_llms_txt uses the correct keyword arguments when calling run_generation.
    Using autospec=True ensures the mock enforces the real function's signature.
    """
    run_store = RunStore()
    
    # autospec=True is the key here: it will raise TypeError if called with wrong args
    with patch("lms_llmstxt_mcp.generator.run_generation", autospec=True) as mock_run:
        # We don't need it to actually do anything, just not crash on call
        mock_run.return_value = pytest.importorskip("lms_llmstxt.models").GenerationArtifacts(
            llms_txt_path="foo",
            llms_full_path="bar",
            used_fallback=False
        )
        
        # This should NOT raise TypeError
        try:
            safe_generate_llms_txt(run_store, run_id=None, url="https://github.com/test/repo")
        except TypeError as e:
            pytest.fail(f"safe_generate called run_generation with incorrect signature: {e}")
        
        # Verify it was called with repo_url, not url
        args, kwargs = mock_run.call_args
        assert "repo_url" in kwargs
        assert "config" in kwargs
        assert "url" not in kwargs
        assert kwargs.get("build_full") is False
        assert kwargs.get("build_ctx") is False
