import pytest
from llmstxt_mcp.runs import RunStore
from llmstxt_mcp.models import GenerateResult
from llmstxt_mcp.errors import UnknownRunError

def test_run_store():
    store = RunStore()
    
    # Empty get
    with pytest.raises(UnknownRunError):
        store.get_run("missing")
        
    # Put
    run1 = GenerateResult(run_id="run1", status="success")
    store.put_run(run1)
    
    # Get
    retrieved = store.get_run("run1")
    assert retrieved == run1
    
    # List
    run2 = GenerateResult(run_id="run2", status="failed")
    store.put_run(run2)
    
    runs = store.list_runs(limit=10)
    assert len(runs) == 2
    assert runs[0].run_id == "run2" # newest first
    assert runs[1].run_id == "run1"
    
    # List limit
    runs_limited = store.list_runs(limit=1)
    assert len(runs_limited) == 1
    assert runs_limited[0].run_id == "run2"
