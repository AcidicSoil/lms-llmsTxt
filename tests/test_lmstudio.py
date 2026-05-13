from __future__ import annotations

from pathlib import Path

import pytest
import requests

from lms_llmsTxt.config import AppConfig
from lms_llmsTxt import pipeline
import lms_llmsTxt.lmstudio as lmstudio
from lms_llmsTxt.lmstudio import LMStudioConnectivityError
from lms_llmsTxt.models import AnalyzerTrace


class _FakeResponse:
    def __init__(self, status_code=200, payload=None, text="OK"):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(self.text)

    def json(self):
        return self._payload


def test_fetch_models_prefers_v1(monkeypatch):
    calls = []

    def fake_get(url, headers=None, timeout=None):
        calls.append(url)
        if url.endswith("/v1/models"):
            return _FakeResponse(
                payload={"data": [{"id": "model-a"}, {"name": "model-b"}]},
            )
        if url.endswith("/models"):
            raise requests.RequestException("legacy endpoint disabled")
        raise AssertionError(f"Unexpected URL {url}")

    monkeypatch.setattr(lmstudio.requests, "get", fake_get)
    config = AppConfig(
        lm_model="model-a",
        lm_api_base="http://localhost:1234/v1",
        lm_api_key="key",
        output_dir=Path("artifacts"),
    )

    lmstudio._ensure_lmstudio_ready(config)

    assert calls[0].endswith("/v1/models")


def test_choose_lmstudio_test_model_prefers_small_available_text_model(monkeypatch):
    def fake_get(url, headers=None, timeout=None):
        return _FakeResponse(
            payload={
                "data": [
                    {"id": "qwen3-vl-reranker-2b"},
                    {"id": "qwen_qwen3.5-9b"},
                    {"id": "qwen_qwen3.5-0.8b"},
                    {"id": "text-embedding-qwen3-embedding-0.6b"},
                ]
            }
        )

    monkeypatch.setattr(lmstudio.requests, "get", fake_get)
    config = AppConfig(
        lm_model="missing-large-model",
        lm_api_base="http://localhost:1234/v1",
        lm_api_key="key",
        output_dir=Path("artifacts"),
    )

    assert lmstudio.choose_lmstudio_test_model(config) == "qwen_qwen3.5-0.8b"


def test_choose_lmstudio_test_model_skips_excluded_configured_model(monkeypatch):
    def fake_get(url, headers=None, timeout=None):
        return _FakeResponse(
            payload={
                "data": [
                    {"id": "qwen_qwen3-vl-4b-instruct"},
                    {"id": "qwen_qwen3.5-0.8b"},
                ]
            }
        )

    monkeypatch.setattr(lmstudio.requests, "get", fake_get)
    config = AppConfig(
        lm_model="qwen_qwen3-vl-4b-instruct",
        lm_api_base="http://localhost:1234/v1",
        lm_api_key="key",
        output_dir=Path("artifacts"),
    )

    assert lmstudio.choose_lmstudio_test_model(config) == "qwen_qwen3.5-0.8b"


def test_choose_lmstudio_test_model_skips_excluded_preferred_model(monkeypatch):
    def fake_get(url, headers=None, timeout=None):
        return _FakeResponse(
            payload={
                "data": [
                    {"id": "qwen3-reranker-0.6b"},
                    {"id": "qwen_qwen3.5-0.8b"},
                ]
            }
        )

    monkeypatch.setattr(lmstudio.requests, "get", fake_get)
    config = AppConfig(
        lm_model=None,
        lm_api_base="http://localhost:1234/v1",
        lm_api_key="key",
        output_dir=Path("artifacts"),
    )

    assert (
        lmstudio.choose_lmstudio_test_model(
            config,
            preferred_model="qwen3-reranker-0.6b",
        )
        == "qwen_qwen3.5-0.8b"
    )


def test_choose_lmstudio_test_model_honors_loaded_preferred_model(monkeypatch):
    def fake_get(url, headers=None, timeout=None):
        return _FakeResponse(
            payload={"data": [{"id": "small-model-1b"}, {"id": "requested-model"}]}
        )

    monkeypatch.setattr(lmstudio.requests, "get", fake_get)
    config = AppConfig(
        lm_model="missing-large-model",
        lm_api_base="http://localhost:1234/v1",
        lm_api_key="key",
        output_dir=Path("artifacts"),
    )

    assert (
        lmstudio.choose_lmstudio_test_model(
            config,
            preferred_model="requested-model",
        )
        == "requested-model"
    )


def test_ensure_ready_attempts_documented_load_for_missing_model(monkeypatch):
    posts = []
    get_calls = 0

    def fake_get(url, headers=None, timeout=None):
        nonlocal get_calls
        get_calls += 1
        if get_calls == 1:
            return _FakeResponse(payload={"data": [{"id": "available-model"}]})
        return _FakeResponse(payload={"data": [{"id": "target"}]})

    def fake_post(url, headers=None, json=None, timeout=None):
        posts.append((url, json))
        return _FakeResponse()

    monkeypatch.setattr(lmstudio.requests, "get", fake_get)
    monkeypatch.setattr(lmstudio.requests, "post", fake_post)
    monkeypatch.setattr(lmstudio, "_LMSTUDIO_SDK", None, raising=False)
    monkeypatch.setattr(lmstudio, "_load_model_cli", lambda config: False)

    config = AppConfig(
        lm_model="target",
        lm_api_base="http://localhost:1234/v1",
        lm_api_key="key",
        output_dir=Path("artifacts"),
        lm_ttl_seconds=123,
        max_context_tokens=4096,
    )

    lmstudio._ensure_lmstudio_ready(config)

    assert posts
    url, body = posts[0]
    assert url.endswith("/api/v1/models/load")
    assert body["model"] == "target"
    assert body["ttl"] == 123
    assert body["context_length"] == 4096


def test_ensure_ready_requires_configured_model(monkeypatch):
    def fake_get(url, headers=None, timeout=None):
        raise AssertionError("LM Studio should not be queried before model config is validated")

    monkeypatch.setattr(lmstudio.requests, "get", fake_get)

    config = AppConfig(
        lm_model=None,
        lm_api_base="http://localhost:1234/v1",
        lm_api_key="key",
        output_dir=Path("artifacts"),
    )

    with pytest.raises(LMStudioConnectivityError, match="LMSTUDIO_MODEL"):
        lmstudio._ensure_lmstudio_ready(config)


def test_app_config_reads_lmstudio_model_from_environment(monkeypatch):
    monkeypatch.setenv("LMSTUDIO_MODEL", "custom-model-from-env")

    config = AppConfig(output_dir=Path("artifacts"))

    assert config.lm_model == "custom-model-from-env"


def test_app_config_does_not_fall_back_to_hardcoded_model(tmp_path, monkeypatch):
    monkeypatch.delenv("LMSTUDIO_MODEL", raising=False)
    monkeypatch.chdir(tmp_path)

    config = AppConfig(output_dir=Path("artifacts"))

    assert config.lm_model is None


def test_ensure_ready_failure(monkeypatch):
    def fake_get(url, headers=None, timeout=None):
        return _FakeResponse(payload={"data": []})

    monkeypatch.setattr(lmstudio.requests, "get", fake_get)
    monkeypatch.setattr(lmstudio, "_load_model_sdk", lambda config: False)
    monkeypatch.setattr(lmstudio, "_load_model_rest", lambda config: False)
    monkeypatch.setattr(lmstudio, "_load_model_cli", lambda config: False)

    config = AppConfig(
        lm_model="missing-model",
        lm_api_base="http://localhost:1234/v1",
        lm_api_key="key",
        output_dir=Path("artifacts"),
    )

    with pytest.raises(LMStudioConnectivityError, match="automatic load failed"):
        lmstudio._ensure_lmstudio_ready(config)


def test_configure_lmstudio_uses_schema_only_json_adapter(monkeypatch):
    configured: dict[str, object] = {}

    def fake_get(url, headers=None, timeout=None):
        return _FakeResponse(payload={"data": [{"id": "model"}]})

    class FakeLM:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    monkeypatch.setattr(lmstudio.requests, "get", fake_get)
    monkeypatch.setattr(lmstudio.dspy, "LM", FakeLM)
    monkeypatch.setattr(lmstudio.dspy, "configure", lambda **kwargs: configured.update(kwargs))

    config = AppConfig(
        lm_model="model",
        lm_api_base="http://localhost:1234/v1",
        lm_api_key="key",
        output_dir=Path("artifacts"),
    )

    lm = lmstudio.configure_lmstudio_lm(config)

    assert configured["lm"] is lm
    adapter = configured["adapter"]
    assert isinstance(adapter, lmstudio.LMStudioJSONAdapter)


def test_pipeline_fallback(tmp_path, monkeypatch, caplog):
    repo_url = "https://github.com/example/repo"
    repo_root = tmp_path / "artifacts"

    def fake_configure(*args, **kwargs):
        raise LMStudioConnectivityError("LM unavailable")

    fake_material = pipeline.RepositoryMaterial(
        repo_url=repo_url,
        file_tree="README.md\nsrc/main.py",
        readme_content="# Title\n\nSummary",
        package_files=(
            "=== selected evidence: src/main.py ===\n"
            "This source file starts the application and wires the main workflow. "
            "It exposes a concrete entry point that graph synthesis can describe."
        ),
        default_branch="main",
        is_private=False,
    )

    class FakeAnalyzer:
        def __call__(self, *args, **kwargs):
            raise AssertionError("Should not be invoked because configure fails")

    monkeypatch.setattr(pipeline, "configure_lmstudio_lm", fake_configure)
    monkeypatch.setattr(pipeline, "prepare_repository_material", lambda *a, **k: fake_material)
    monkeypatch.setattr(pipeline, "RepositoryAnalyzer", lambda: FakeAnalyzer())
    config = AppConfig(
        lm_model="missing",
        lm_api_base="http://localhost:1234/v1",
        lm_api_key="key",
        output_dir=repo_root,
    )

    artifacts = pipeline.run_generation(repo_url, config, build_ctx=False)

    assert "LM generation unavailable; using fallback output. Reason: LM unavailable" in caplog.text
    assert artifacts.used_fallback is True
    assert artifacts.fallback_reason == "LM unavailable"
    assert Path(artifacts.llms_txt_path).exists()
    assert Path(artifacts.llms_full_path).exists()
    assert Path(artifacts.json_path).exists()


def test_pipeline_unloads_model(tmp_path, monkeypatch):
    repo_url = "https://github.com/example/repo"
    repo_root = tmp_path / "artifacts"

    fake_material = pipeline.RepositoryMaterial(
        repo_url=repo_url,
        file_tree="README.md\nsrc/main.py",
        readme_content="# Title\n\nSummary",
        package_files="",
        default_branch="main",
        is_private=False,
    )

    class FakeAnalyzer:
        def __call__(self, *args, **kwargs):
            return type("Result", (), {"llms_txt_content": "# Generated\n"})()

    unload_called = {}

    monkeypatch.setattr(pipeline, "prepare_repository_material", lambda *a, **k: fake_material)
    monkeypatch.setattr(pipeline, "RepositoryAnalyzer", lambda: FakeAnalyzer())
    monkeypatch.setattr(pipeline, "configure_lmstudio_lm", lambda *a, **k: None)
    monkeypatch.setattr(
        pipeline,
        "build_llms_full_from_repo",
        lambda content, **_: content + "\n--- full ---\n",
    )
    monkeypatch.setattr(
        pipeline,
        "unload_lmstudio_model",
        lambda cfg: unload_called.setdefault("done", True),
    )

    config = AppConfig(
        lm_model="model",
        lm_api_base="http://localhost:1234/v1",
        lm_api_key="key",
        output_dir=repo_root,
        lm_auto_unload=True,
    )

    artifacts = pipeline.run_generation(repo_url, config, build_ctx=False)

    assert unload_called.get("done") is True
    assert Path(artifacts.llms_txt_path).exists()
    assert Path(artifacts.llms_full_path).exists()


def test_pipeline_runs_evidence_planning_before_compaction(tmp_path, monkeypatch):
    repo_url = "https://github.com/example/repo"
    repo_root = tmp_path / "artifacts"

    fake_material = pipeline.RepositoryMaterial(
        repo_url=repo_url,
        file_tree="\n".join(["README.md", "docs/getting-started.md", "src/cli.py", "src/internal/worker.py"]),
        readme_content="# Title\n\nSummary",
        package_files="[project]\nname='demo'",
        default_branch="main",
        is_private=False,
    )

    class FakeAnalyzer:
        def __call__(self, *args, **kwargs):
            return type(
                "Result",
                (),
                {
                    "llms_txt_content": "# Generated\n",
                    "trace": AnalyzerTrace(),
                },
            )()

    compact_inputs = []

    class FakeBudget:
        def __init__(self, estimated, available, decision):
            self.estimated_prompt_tokens = estimated
            self.available_tokens = available
            self.decision = decision

    decisions = iter(
        [
            FakeBudget(estimated=4000, available=1000, decision=pipeline.BudgetDecision.NEEDS_COMPACTION),
            FakeBudget(estimated=1200, available=1000, decision=pipeline.BudgetDecision.NEEDS_COMPACTION),
            FakeBudget(estimated=700, available=1000, decision=pipeline.BudgetDecision.APPROVED),
        ]
    )

    monkeypatch.setattr(pipeline, "prepare_repository_material", lambda *a, **k: fake_material)
    monkeypatch.setattr(pipeline, "RepositoryAnalyzer", lambda *args, **kwargs: FakeAnalyzer())
    monkeypatch.setattr(pipeline, "configure_lmstudio_lm", lambda *a, **k: None)
    monkeypatch.setattr(pipeline, "build_context_budget", lambda *a, **k: next(decisions))
    monkeypatch.setattr(pipeline, "suggested_evidence_limit", lambda *a, **k: 2)
    monkeypatch.setattr(
        pipeline,
        "fetch_file_content",
        lambda owner, repo, path, ref, token: f"selected content for {path}",
    )
    monkeypatch.setattr(
        pipeline,
        "compact_material",
        lambda material, *args, **kwargs: compact_inputs.append(material.file_tree.splitlines()) or material,
    )
    monkeypatch.setattr(
        pipeline,
        "build_llms_full_from_repo",
        lambda content, **_: content + "\n--- full ---\n",
    )

    config = AppConfig(
        lm_model="model",
        lm_api_base="http://localhost:1234/v1",
        lm_api_key="key",
        output_dir=repo_root,
    )

    artifacts = pipeline.run_generation(repo_url, config, build_ctx=False)

    assert compact_inputs
    assert len(compact_inputs[0]) < len(fake_material.file_tree.splitlines())
    assert Path(artifacts.trace_path).exists()
    trace_text = Path(artifacts.trace_path).read_text(encoding="utf-8")
    assert '"stage": "evidence-planning"' in trace_text
    assert '"content_fetched": true' in trace_text
    assert '"evidence_budget"' in trace_text
    assert '"candidate_count": 4' in trace_text
    assert '"max_paths": 2' in trace_text
    assert '"budget_reason": "candidate-count-exceeds-limit"' in trace_text
    assert 'Selective evidence planning ran before deterministic compaction.' in trace_text


def test_unload_prefers_sdk(monkeypatch):
    handle_unloaded = {}

    class FakeHandle:
        identifier = "model"
        model_key = "model"

        def unload(self):
            handle_unloaded["done"] = True

    class FakeSDK:
        def __init__(self):
            self.hosts = []

        def configure_default_client(self, host):
            self.hosts.append(host)

        def list_loaded_models(self, kind=None):
            return [FakeHandle()]

    fake_sdk = FakeSDK()
    monkeypatch.setattr(lmstudio, "_LMSTUDIO_SDK", fake_sdk, raising=False)

    def should_not_run(*args, **kwargs):
        raise AssertionError("Fallback path should not execute when SDK succeeds")

    monkeypatch.setattr(lmstudio, "_unload_model_http", should_not_run, raising=False)
    monkeypatch.setattr(lmstudio, "_unload_model_cli", should_not_run, raising=False)

    config = AppConfig(
        lm_model="model",
        lm_api_base="http://localhost:1234/v1",
        lm_api_key=None,
        output_dir=Path("artifacts"),
    )

    lmstudio.unload_lmstudio_model(config)

    assert handle_unloaded.get("done") is True
    assert fake_sdk.hosts == ["localhost:1234"]


def test_lmstudio_json_adapter_sets_schema_response_format_without_json_object():
    class DemoSignature(lmstudio.dspy.Signature):
        question: str = lmstudio.dspy.InputField()
        answer: str = lmstudio.dspy.OutputField()
        bullets: list[str] = lmstudio.dspy.OutputField()

    adapter = lmstudio.LMStudioJSONAdapter()
    lm_kwargs: dict[str, object] = {}

    adapter._apply_response_schema(lm_kwargs, DemoSignature)

    response_format = lm_kwargs["response_format"]
    assert response_format != {"type": "json_object"}
    assert hasattr(response_format, "model_json_schema")
    schema = response_format.model_json_schema()
    assert set(schema["properties"]) == {"answer", "bullets"}
    assert schema["required"] == ["answer", "bullets"]


def test_generate_graph_auto_skips_dspy_enrichment_for_large_evidence(tmp_path, monkeypatch):
    repo_url = "https://github.com/example/repo"
    repo_root = tmp_path / "artifacts"

    fake_material = pipeline.RepositoryMaterial(
        repo_url=repo_url,
        file_tree="\n".join(f"src/file_{index}.py" for index in range(300)),
        readme_content="# Title\n\nSummary",
        package_files="x" * 40_000,
        default_branch="main",
        is_private=False,
    )

    class FakeAnalyzer:
        def __call__(self, *args, **kwargs):
            return type("Result", (), {"llms_txt_content": "# Generated\n"})()

    monkeypatch.setattr(pipeline, "prepare_repository_material", lambda *a, **k: fake_material)
    monkeypatch.setattr(pipeline, "RepositoryAnalyzer", lambda: FakeAnalyzer())
    monkeypatch.setattr(pipeline, "configure_lmstudio_lm", lambda *a, **k: None)
    monkeypatch.setattr(pipeline, "unload_lmstudio_model", lambda cfg: None)
    monkeypatch.setattr(
        pipeline,
        "enrich_repo_graph_with_dspy",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("large graph should skip DSPy enrichment automatically")),
    )

    config = AppConfig(
        lm_model="model",
        lm_api_base="http://localhost:1234/v1",
        lm_api_key="key",
        output_dir=repo_root,
        enable_repo_graph=True,
        lm_auto_unload=True,
    )

    artifacts = pipeline.run_generation(repo_url, config, build_ctx=False, build_full=False)

    assert Path(artifacts.graph_json_path).exists()
    assert Path(artifacts.force_graph_path).exists()
    assert Path(artifacts.graph_nodes_dir).exists()


def test_generate_graph_auto_attempts_dspy_enrichment_for_small_evidence(tmp_path, monkeypatch):
    repo_url = "https://github.com/example/repo"
    repo_root = tmp_path / "artifacts"

    fake_material = pipeline.RepositoryMaterial(
        repo_url=repo_url,
        file_tree="README.md\nsrc/main.py",
        readme_content="# Title\n\nSummary",
        package_files=(
            "=== selected evidence: src/main.py ===\n"
            "This source file starts the application and wires the main workflow. "
            "It exposes a concrete entry point that graph synthesis can describe."
        ),
        default_branch="main",
        is_private=False,
    )

    class FakeAnalyzer:
        def __call__(self, *args, **kwargs):
            return type("Result", (), {"llms_txt_content": "# Generated\n"})()

    enrichment_called = {"value": False}

    def fake_enrich_graph(graph, digest, material, config):
        enrichment_called["value"] = True
        return graph

    monkeypatch.setattr(pipeline, "prepare_repository_material", lambda *a, **k: fake_material)
    monkeypatch.setattr(pipeline, "RepositoryAnalyzer", lambda: FakeAnalyzer())
    monkeypatch.setattr(pipeline, "configure_lmstudio_lm", lambda *a, **k: None)
    monkeypatch.setattr(pipeline, "unload_lmstudio_model", lambda cfg: None)
    monkeypatch.setattr(pipeline, "enrich_repo_graph_with_dspy", fake_enrich_graph)

    config = AppConfig(
        lm_model="qwen-7b",
        lm_api_base="http://localhost:1234/v1",
        lm_api_key="key",
        output_dir=repo_root,
        enable_repo_graph=True,
    )

    artifacts = pipeline.run_generation(repo_url, config, build_ctx=False, build_full=False)

    assert enrichment_called["value"] is True
    assert Path(artifacts.graph_json_path).exists()
