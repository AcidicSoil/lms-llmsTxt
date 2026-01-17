from pathlib import Path

from lms_llmsTxt.config import AppConfig


_ENV_KEYS = [
    "LMSTUDIO_MODEL",
    "LMSTUDIO_BASE_URL",
    "LMSTUDIO_API_KEY",
    "OUTPUT_DIR",
    "LINK_STYLE",
    "ENABLE_CTX",
    "LMSTUDIO_STREAMING",
    "LMSTUDIO_AUTO_UNLOAD",
]


def _clear_env(monkeypatch) -> None:
    for key in _ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_app_config_defaults(monkeypatch):
    _clear_env(monkeypatch)
    config = AppConfig()

    assert config.lm_model == "qwen_qwen3-vl-4b-instruct"
    assert config.lm_api_base == "http://localhost:1234/v1"
    assert config.lm_api_key == "lm-studio"
    assert config.output_dir == Path("artifacts")
    assert config.link_style == "blob"
    assert config.enable_ctx is False
    assert config.lm_streaming is True
    assert config.lm_auto_unload is True


def test_app_config_env_overrides(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    monkeypatch.setenv("LMSTUDIO_MODEL", "model-x")
    monkeypatch.setenv("LMSTUDIO_BASE_URL", "http://example.test/v1")
    monkeypatch.setenv("LMSTUDIO_API_KEY", "secret")
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path))
    monkeypatch.setenv("LINK_STYLE", "raw")
    monkeypatch.setenv("ENABLE_CTX", "1")
    monkeypatch.setenv("LMSTUDIO_STREAMING", "0")
    monkeypatch.setenv("LMSTUDIO_AUTO_UNLOAD", "false")

    config = AppConfig()

    assert config.lm_model == "model-x"
    assert config.lm_api_base == "http://example.test/v1"
    assert config.lm_api_key == "secret"
    assert config.output_dir == Path(str(tmp_path))
    assert config.link_style == "raw"
    assert config.enable_ctx is True
    assert config.lm_streaming is False
    assert config.lm_auto_unload is False
