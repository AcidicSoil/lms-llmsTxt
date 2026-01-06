import pytest
from pydantic import ValidationError
from lms_llmsTxt_mcp.models import GenerateResult, ArtifactRef, ReadArtifactResult

def test_artifact_ref_validation():
    ref = ArtifactRef(name="llms.txt", path="/tmp/foo", size_bytes=100, hash_sha256="abc")
    assert ref.name == "llms.txt"
    
    with pytest.raises(ValidationError):
        ArtifactRef(name="invalid.txt", path="/tmp/foo", size_bytes=100, hash_sha256="abc")

def test_generate_result_validation():
    res = GenerateResult(run_id="123", status="completed")
    assert res.run_id == "123"
    assert res.artifacts == []
    
    with pytest.raises(ValidationError):
        GenerateResult(run_id="123", status="invalid") # pending not allowed in Literal

def test_read_artifact_result():
    res = ReadArtifactResult(content="foo", truncated=False, total_chars=3)
    assert res.content == "foo"
