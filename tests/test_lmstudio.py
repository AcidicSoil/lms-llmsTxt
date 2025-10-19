from __future__ import annotations

from pathlib import Path

import pytest
import requests

from lmstudiotxt_generator.config import AppConfig
from lmstudiotxt_generator import pipeline
import lmstudiotxt_generator.lmstudio as lmstudio
from lmstudiotxt_generator.lmstudio import LMStudioConnectivityError


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


def test_ensure_ready_auto_load(monkeypatch):
    sequence = [
        _FakeResponse(payload={"data": []}),
        _FakeResponse(payload={"data": [{"id": "target"}]}),
    ]
    posts = []

    def fake_get(url, headers=None, timeout=None):
        return sequence.pop(0)

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

    lmstudio._ensure_lmstudio_ready(config)

    assert posts  # auto-load attempted


def test_ensure_ready_failure(monkeypatch):
    def fake_get(url, headers=None, timeout=None):
        return _FakeResponse(payload={"data": []})

    def fake_post(url, headers=None, json=None, timeout=None):
        return _FakeResponse(status_code=404, text="missing")

    monkeypatch.setattr(lmstudio.requests, "get", fake_get)
    monkeypatch.setattr(lmstudio.requests, "post", fake_post)
    monkeypatch.setattr(
        lmstudio,
        "_load_model_cli",
        lambda model: False,
    )

    config = AppConfig(
        lm_model="missing-model",
        lm_api_base="http://localhost:1234/v1",
        lm_api_key="key",
        output_dir=Path("artifacts"),
    )

    with pytest.raises(LMStudioConnectivityError):
        lmstudio._ensure_lmstudio_ready(config)


def test_pipeline_fallback(tmp_path, monkeypatch):
    repo_url = "https://github.com/example/repo"
    repo_root = tmp_path / "artifacts"

    def fake_configure(*args, **kwargs):
        raise LMStudioConnectivityError("LM unavailable")

    fake_material = pipeline.RepositoryMaterial(
        repo_url=repo_url,
        file_tree="README.md\nsrc/main.py",
        readme_content="# Title\n\nSummary",
        package_files="",
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

    artifacts = pipeline.run_generation(repo_url, config)

    assert artifacts.used_fallback is True
    assert Path(artifacts.llms_txt_path).exists()
    assert Path(artifacts.llms_full_path).exists()
    assert Path(artifacts.json_path).exists()
