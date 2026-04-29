from __future__ import annotations

from lms_llmsTxt.config import AppConfig


_ENV_KEYS = (
    "LMSTUDIO_MODEL",
    "LMSTUDIO_BASE_URL",
    "LMSTUDIO_API_KEY",
    "OUTPUT_DIR",
)


def test_app_config_reads_lmstudio_model_from_environment(monkeypatch):
    monkeypatch.setenv("LMSTUDIO_MODEL", "custom/local-model")

    config = AppConfig()

    assert config.lm_model == "custom/local-model"


def test_app_config_has_no_hardcoded_lmstudio_model_default(tmp_path, monkeypatch):
    monkeypatch.delenv("LMSTUDIO_MODEL", raising=False)
    monkeypatch.chdir(tmp_path)

    config = AppConfig()

    assert config.lm_model is None


def test_app_config_refreshes_dotenv_before_reading_values(tmp_path, monkeypatch):
    for key in _ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.chdir(tmp_path)
    tmp_path.joinpath(".env").write_text(
        "LMSTUDIO_MODEL=dotenv-model\n"
        "LMSTUDIO_BASE_URL=http://localhost:9999/v1\n"
        "LMSTUDIO_API_KEY=dotenv-key\n"
        "OUTPUT_DIR=dotenv-artifacts\n",
        encoding="utf-8",
    )

    config = AppConfig()

    assert config.lm_model == "dotenv-model"
    assert config.lm_api_base == "http://localhost:9999/v1"
    assert config.lm_api_key == "dotenv-key"
    assert str(config.output_dir) == "dotenv-artifacts"


def test_process_environment_overrides_dotenv_file(tmp_path, monkeypatch):
    for key in _ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.chdir(tmp_path)
    tmp_path.joinpath(".env").write_text(
        "LMSTUDIO_MODEL=dotenv-model\n"
        "LMSTUDIO_BASE_URL=http://localhost:9999/v1\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("LMSTUDIO_MODEL", "shell-model")

    config = AppConfig()

    assert config.lm_model == "shell-model"
    assert config.lm_api_base == "http://localhost:9999/v1"
