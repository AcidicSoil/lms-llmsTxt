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


def test_ensure_ready_does_not_auto_load_missing_model(monkeypatch):
    posts = []

    def fake_get(url, headers=None, timeout=None):
        return _FakeResponse(payload={"data": [{"id": "available-model"}]})

    def fake_post(url, headers=None, json=None, timeout=None):
        posts.append((url, json))
        return _FakeResponse()

    monkeypatch.setattr(lmstudio.requests, "get", fake_get)
    monkeypatch.setattr(lmstudio.requests, "post", fake_post)

    config = AppConfig(
        lm_model="target",
        lm_api_base="http://localhost:1234/v1",
        lm_api_key="key",
        output_dir=Path("artifacts"),
    )

    with pytest.raises(LMStudioConnectivityError, match="Download and load"):
        lmstudio._ensure_lmstudio_ready(config)

    assert posts == []


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

    config = AppConfig(
        lm_model="missing-model",
        lm_api_base="http://localhost:1234/v1",
        lm_api_key="key",
        output_dir=Path("artifacts"),
    )

    with pytest.raises(LMStudioConnectivityError, match="missing-model"):
        lmstudio._ensure_lmstudio_ready(config)


def test_pipeline_fallback(tmp_path, monkeypatch, caplog):
    repo_url = "https://github.com/example/repo"
    repo_root = tmp_path / "artifacts"

    def fake_configure(*args, **kwargs):
        raise LMStudioConnectivityError("LM unavailable")

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
