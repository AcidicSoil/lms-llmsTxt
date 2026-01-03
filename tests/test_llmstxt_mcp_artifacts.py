from pathlib import Path
from llmstxt_mcp.artifacts import resource_uri, read_resource_text, read_artifact_chunk
from llmstxt_mcp.runs import RunStore
from llmstxt_mcp.models import GenerateResult, ArtifactRef
from llmstxt_mcp.config import settings

def test_resource_uri():
    assert resource_uri("123", "llms.txt") == "llmstxt://runs/123/llms.txt"

def test_read_resource_text(tmp_path):
    settings.LLMSTXT_MCP_RESOURCE_MAX_CHARS = 10
    store = RunStore()
    f = tmp_path / "llms.txt"
    f.write_text("123456789012345", encoding="utf-8")
    
    run = GenerateResult(
        run_id="run1", 
        status="success",
        artifacts=[
            ArtifactRef(name="llms.txt", path=str(f), size_bytes=15, hash_sha256="abc")
        ]
    )
    store.put_run(run)
    
    content = read_resource_text(store, "run1", "llms.txt")
    assert content == "1234567890\n... (content truncated)"

def test_read_artifact_chunk(tmp_path):
    store = RunStore()
    f = tmp_path / "numbers.txt"
    f.write_text("0123456789", encoding="utf-8")
    
    run = GenerateResult(
        run_id="run1", 
        status="success",
        artifacts=[
            ArtifactRef(name="llms.txt", path=str(f), size_bytes=10, hash_sha256="abc")
        ]
    )
    store.put_run(run)
    
    # Normal read: offset 2, limit 3 -> 2,3,4
    assert read_artifact_chunk(store, "run1", "llms.txt", 2, 3) == "234"
    
    # Read past EOF: offset 8 ('8'), limit 5 -> '89'
    assert read_artifact_chunk(store, "run1", "llms.txt", 8, 5) == "89"
    
    # Read beyond EOF
    assert read_artifact_chunk(store, "run1", "llms.txt", 15, 5) == ""
