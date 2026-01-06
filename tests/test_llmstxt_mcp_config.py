import os
from pathlib import Path
import pytest
from lms_llmstxt_mcp.config import Settings
from lms_llmstxt_mcp.errors import OutputDirNotAllowedError, LMStudioUnavailableError

def test_config_defaults():
    # Ensure env vars don't interfere if they happen to be set
    old_val = os.environ.get("LLMSTXT_MCP_RESOURCE_MAX_CHARS")
    if old_val:
        del os.environ["LLMSTXT_MCP_RESOURCE_MAX_CHARS"]
        
    settings = Settings()
    assert settings.LLMSTXT_MCP_ALLOWED_ROOT == Path("./artifacts")
    assert settings.LLMSTXT_MCP_RESOURCE_MAX_CHARS == 100000
    
    if old_val:
        os.environ["LLMSTXT_MCP_RESOURCE_MAX_CHARS"] = old_val

def test_config_env_vars():
    os.environ["LLMSTXT_MCP_RESOURCE_MAX_CHARS"] = "500"
    try:
        settings = Settings()
        assert settings.LLMSTXT_MCP_RESOURCE_MAX_CHARS == 500
    finally:
        del os.environ["LLMSTXT_MCP_RESOURCE_MAX_CHARS"]

def test_custom_errors():
    with pytest.raises(OutputDirNotAllowedError):
        raise OutputDirNotAllowedError("Not allowed")
    with pytest.raises(LMStudioUnavailableError):
        raise LMStudioUnavailableError("Unavailable")