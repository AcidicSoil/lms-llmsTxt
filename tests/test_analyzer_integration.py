from pathlib import Path

import pytest

from lms_llmsTxt.config import AppConfig
from lms_llmsTxt.lmstudio import LMStudioConnectivityError, choose_lmstudio_test_model


@pytest.mark.integration
def test_lmstudio_advertises_small_text_model_for_analyzer_smoke():
    """
    Smoke-test LM Studio endpoint/model availability without running DSPy generation.

    Full analyzer runs are intentionally excluded from pytest because they load an
    LLM and consume generation resources. Use manual smoke scripts for full
    generation when explicitly needed.
    """
    config = AppConfig(output_dir=Path("artifacts"))
    try:
        selected_model = choose_lmstudio_test_model(config)
    except LMStudioConnectivityError as exc:
        pytest.skip(f"Skipping LM Studio endpoint smoke: {exc}")

    assert selected_model
    assert not any(
        marker in selected_model.lower()
        for marker in ("embedding", "rerank", "reranker", "vl", "vision", "ocr")
    )
