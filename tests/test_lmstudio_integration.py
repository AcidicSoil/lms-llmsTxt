import os
from pathlib import Path

import pytest
from requests import HTTPError

from lms_llmsTxt.config import AppConfig
from lms_llmsTxt.pipeline import run_generation

@pytest.mark.integration
def test_real_generation(tmp_path):
    """
    Real integration test against running LM Studio.
    Requires GITHUB_ACCESS_TOKEN.
    """
    repo_url = "https://github.com/AcidicSoil/lms-llmsTxt" # This repo
    output_dir = tmp_path / "artifacts"
    
    config = AppConfig(
        lm_model="qwen_qwen3-vl-4b-instruct",
        lm_api_base="http://localhost:1234/v1",
        output_dir=output_dir,
        lm_auto_unload=False # Don't unload user's model
    )
    
    # Check for GH token
    if not os.environ.get("GITHUB_ACCESS_TOKEN") and not os.environ.get("GH_TOKEN"):
        pytest.skip("Skipping integration test: GITHUB_ACCESS_TOKEN not set")

    try:
        artifacts = run_generation(repo_url, config, build_ctx=False)
    except HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else None
        if status_code in {401, 403}:
            pytest.skip("Skipping integration test: GitHub token is invalid or unauthorized")
        raise
    
    assert artifacts.used_fallback is False
    assert Path(artifacts.llms_txt_path).exists()
    assert Path(artifacts.llms_full_path).exists()
    
    # Verify content looks like a valid llms.txt
    content = Path(artifacts.llms_txt_path).read_text()
    assert "# " in content # Title
    assert "> " in content # Description
    assert "- [" in content # Links
