import os
from pathlib import Path
import pytest
import dspy
from lms_llmsTxt.analyzer import RepositoryAnalyzer
from lms_llmsTxt.lmstudio import configure_lmstudio_lm
from lms_llmsTxt.config import AppConfig
from lms_llmsTxt.models import RepositoryMaterial

def test_analyzer_integration():
    """
    Test the DSPy analyzer against a real LM Studio instance.
    """
    config = AppConfig(
        lm_model="qwen_qwen3-vl-4b-instruct",
        lm_api_base="http://localhost:1234/v1",
        output_dir=Path("artifacts"),
    )
    
    configure_lmstudio_lm(config)
    
    analyzer = RepositoryAnalyzer()
    
    material = RepositoryMaterial(
        repo_url="https://github.com/AcidicSoil/lms-llmsTxt",
        file_tree="README.md\npyproject.toml\nsrc/lms_llmsTxt/pipeline.py",
        readme_content="# LMS LLMSTXT\n\nA generator for llms.txt files.",
        package_files="pyproject.toml content",
        default_branch="main",
        is_private=False
    )
    
    # Pass arguments individually as expected by forward()
    result = analyzer(
        repo_url=material.repo_url,
        file_tree=material.file_tree,
        readme_content=material.readme_content,
        package_files=material.package_files,
        default_branch=material.default_branch,
        is_private=material.is_private,
        github_token=config.github_token,
    )
    
    assert hasattr(result, "llms_txt_content")
    assert len(result.llms_txt_content) > 50
    print(f"\nGenerated llms.txt content:\n{result.llms_txt_content}")
