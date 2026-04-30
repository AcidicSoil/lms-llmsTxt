from pathlib import Path

import pytest

from lms_llmsTxt.config import AppConfig
from lms_llmsTxt.lmstudio import LMStudioConnectivityError, choose_lmstudio_test_model


@pytest.mark.integration
def test_lmstudio_models_endpoint_supports_generation_test_model(tmp_path):
    """
    Verify LM Studio's models endpoint can provide a small text model.

    This deliberately does not call run_generation(); pytest should not perform a
    full repository generation or load a large model as part of routine tests.
    """
    config = AppConfig(output_dir=tmp_path / "artifacts")
    try:
        selected_model = choose_lmstudio_test_model(config)
    except LMStudioConnectivityError as exc:
        pytest.skip(f"Skipping LM Studio endpoint smoke: {exc}")

    assert selected_model
    assert isinstance(selected_model, str)
