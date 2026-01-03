import json
from llmstxt_mcp.server import run_store
from llmstxt_mcp.models import GenerateResult, ArtifactRef
import pytest

def test_list_runs_tool():
    # Manually populate store
    run = GenerateResult(
        run_id="test-run", 
        status="success", 
        artifacts=[]
    )
    run_store.put_run(run)
    
    from llmstxt_mcp.server import list_runs
    
    # Returns JSON string now
    json_res = list_runs(limit=10)
    results = json.loads(json_res)
    assert len(results) >= 1
    assert results[0]["run_id"] == "test-run"

def test_read_artifact_tool(tmp_path):
    # Setup artifact
    f = tmp_path / "llms.txt"
    f.write_text("12345")
    
    run = GenerateResult(
        run_id="read-test",
        status="success",
        artifacts=[ArtifactRef(name="llms.txt", path=str(f), size_bytes=5, hash_sha256="abc")]
    )
    run_store.put_run(run)
    
    from llmstxt_mcp.server import read_artifact
    
    # Returns JSON string
    json_res = read_artifact(run_id="read-test", artifact_name="llms.txt", offset=0, limit=100)
    result = json.loads(json_res)
    assert result["content"] == "12345"
    assert result["total_chars"] == 5
    assert result["truncated"] is False

def test_resource_access(tmp_path):
    # Setup artifact
    f = tmp_path / "res.txt"
    f.write_text("resource content")
    
    run = GenerateResult(
        run_id="res-test",
        status="success",
        artifacts=[ArtifactRef(name="llms.txt", path=str(f), size_bytes=16, hash_sha256="abc")]
    )
    run_store.put_run(run)
    
    from llmstxt_mcp.server import get_run_artifact
    
    content = get_run_artifact(run_id="res-test", artifact_name="llms.txt")
    assert content == "resource content"
