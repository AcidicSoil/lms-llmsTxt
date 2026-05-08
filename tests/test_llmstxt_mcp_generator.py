import pytest
from unittest.mock import patch
from pathlib import Path
from lms_llmsTxt_mcp.generator import safe_generate_llms_txt
from lms_llmsTxt_mcp.errors import OutputDirNotAllowedError
from lms_llmsTxt_mcp.runs import RunStore
from lms_llmsTxt_mcp.models import RunRecord
from lms_llmsTxt_mcp.config import settings
from lms_llmsTxt.models import GenerationArtifacts

@pytest.fixture
def run_store():
    return RunStore()

def test_safe_generate_llms_txt_success(run_store, tmp_path):
    # Setup mock artifacts
    f1 = tmp_path / "llms.txt"
    f1.write_text("content")
    graph = tmp_path / "repo.graph.json"
    graph.write_text("{}")
    run_events = tmp_path / "run.events.jsonl"
    run_events.write_text("{}\n")

    # Configure allowed root
    settings.LLMSTXT_MCP_ALLOWED_ROOT = tmp_path

    mock_artifacts = GenerationArtifacts(
        llms_txt_path=str(f1),
        llms_full_path=None,
        ctx_path=None,
        json_path=None,
        graph_json_path=str(graph),
        run_events_path=str(run_events),
        used_fallback=False
    )

    with patch("lms_llmsTxt_mcp.generator.run_generation", return_value=mock_artifacts) as mock_run:
        # Pass run_id=None to generate a new one
        result = safe_generate_llms_txt(
            run_store=run_store,
            run_id=None,
            url="https://github.com/foo/bar",
            output_dir=str(tmp_path),
            generate_graph=True,
            verbose_budget=True,
            enable_session_memory=True,
        )
        
        assert result.status == "completed"
        artifact_names = {artifact.name for artifact in result.artifacts}
        assert {"llms.txt", "repo.graph.json", "run.events.jsonl"} <= artifact_names
        mock_run.assert_called_once()
        assert mock_run.call_args.kwargs["generate_graph"] is True
        assert mock_run.call_args.kwargs["verbose_budget"] is True
        assert mock_run.call_args.kwargs["enable_session_memory"] is True

def test_safe_generate_llms_txt_syncs_core_generation_options_and_artifacts(run_store, tmp_path):
    files = {
        "llms_txt_path": tmp_path / "llms.txt",
        "json_path": tmp_path / "llms.json",
        "graph_json_path": tmp_path / "repo.graph.json",
        "force_graph_path": tmp_path / "repo.force.json",
        "trace_path": tmp_path / "trace.json",
        "run_log_path": tmp_path / "run.log",
        "run_events_path": tmp_path / "run.events.jsonl",
    }
    for path in files.values():
        path.write_text("content")

    settings.LLMSTXT_MCP_ALLOWED_ROOT = tmp_path

    mock_artifacts = GenerationArtifacts(
        llms_txt_path=str(files["llms_txt_path"]),
        json_path=str(files["json_path"]),
        graph_json_path=str(files["graph_json_path"]),
        force_graph_path=str(files["force_graph_path"]),
        trace_path=str(files["trace_path"]),
        run_log_path=str(files["run_log_path"]),
        run_events_path=str(files["run_events_path"]),
        used_fallback=False,
    )

    with patch("lms_llmsTxt_mcp.generator.run_generation", return_value=mock_artifacts) as mock_run:
        result = safe_generate_llms_txt(
            run_store=run_store,
            run_id=None,
            url="https://github.com/foo/bar",
            output_dir=str(tmp_path),
            cache_lm=False,
            generate_graph=True,
            verbose_budget=True,
            enable_session_memory=True,
        )

    _, kwargs = mock_run.call_args
    assert kwargs["generate_graph"] is True
    assert kwargs["verbose_budget"] is True
    assert kwargs["enable_session_memory"] is True
    assert kwargs["cache_lm"] is False
    assert {artifact.name for artifact in result.artifacts} == {
        "llms.txt",
        "llms.json",
        "repo.graph.json",
        "repo.force.json",
        "trace.json",
        "run.log",
        "run.events.jsonl",
    }


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

    with patch("lms_llmsTxt_mcp.generator.run_generation") as mock_run:
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