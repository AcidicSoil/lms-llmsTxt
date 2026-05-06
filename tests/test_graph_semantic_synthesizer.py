from __future__ import annotations

import pytest

from lms_llmsTxt.config import AppConfig
from lms_llmsTxt.graph_semantic_synthesizer import (
    SemanticGraphSynthesisError,
    _chat_completion_payload,
    _response_error_detail,
    build_semantic_repo_graph,
)
from lms_llmsTxt.models import RepositoryMaterial
from lms_llmsTxt.repo_digest import RepoDigest


def _config() -> AppConfig:
    return AppConfig(
        lm_model="local/test-model",
        lm_api_base="http://localhost:1234/v1",
        lm_api_key="lm-studio",
    )


def _digest() -> RepoDigest:
    return RepoDigest(
        topic="Example Repo",
        architecture_summary="Adapters and examples",
        primary_language="typescript",
        subsystems=[
            {
                "name": "examples/basic",
                "paths": ["examples/basic/index.ts"],
                "summary": "Basic browser automation example",
                "key_symbols": ["main"],
            }
        ],
        key_dependencies=["@hyperbrowser/sdk"],
        entry_points=["examples/basic/index.ts"],
        test_coverage_hint="no_tests_detected",
        digest_id="abc123",
    )


def _material() -> RepositoryMaterial:
    return RepositoryMaterial(
        repo_url="https://github.com/example/repo",
        file_tree="examples/basic/index.ts",
        readme_content="# Example Repo\n\nShows browser automation examples.",
        package_files="=== selected evidence: examples/basic/index.ts ===\nexport async function main() {}",
        default_branch="main",
        is_private=False,
    )


def test_semantic_graph_payload_uses_lmstudio_json_schema_response_format():
    payload = _chat_completion_payload(_digest(), _material(), _config())

    assert payload["response_format"]["type"] == "json_schema"
    assert payload["response_format"]["json_schema"]["name"] == "repo_skill_graph"
    assert payload["response_format"]["json_schema"]["schema"]["required"] == ["topic", "nodes"]


def test_semantic_graph_payload_includes_lmstudio_ttl():
    config = _config()
    config.lm_ttl_seconds = 123

    payload = _chat_completion_payload(_digest(), _material(), config)

    assert payload["ttl"] == 123


def test_response_error_detail_includes_lmstudio_error_body():
    class Response:
        reason = "Bad Request"
        text = '{"error":"unsupported response_format json_object"}'

        def json(self):
            return {"error": "unsupported response_format json_object"}

    assert "unsupported response_format" in _response_error_detail(Response())


def test_semantic_graph_http_error_preserves_response_body(monkeypatch: pytest.MonkeyPatch):
    class Response:
        status_code = 400
        reason = "Bad Request"
        text = '{"error":"unsupported response_format"}'

        def json(self):
            return {"error": "unsupported response_format"}

    def fake_post(*args, **kwargs):
        return Response()

    monkeypatch.setattr("lms_llmsTxt.graph_semantic_synthesizer.requests.post", fake_post)

    with pytest.raises(SemanticGraphSynthesisError, match="unsupported response_format"):
        build_semantic_repo_graph(_digest(), _material(), _config())
