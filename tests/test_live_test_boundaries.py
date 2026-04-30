from __future__ import annotations

import ast
from pathlib import Path


_TEST_ROOT = Path(__file__).parent
_FORBIDDEN_LIVE_GENERATION_NAMES = {
    "RepositoryAnalyzer",
    "configure_lmstudio_lm",
    "run_generation",
    "unload_lmstudio_model",
}
_ALLOWED_FILES = {
    # Unit tests may reference run_generation with monkeypatches/fakes.
    "test_lmstudio.py",
    "test_analyzer.py",
    "test_cli_ui.py",
    "test_llmstxt_mcp_generator.py",
    "test_llmstxt_mcp_generate_signature.py",
    "test_live_test_boundaries.py",
}


def _iter_test_python_files() -> list[Path]:
    return sorted(
        path
        for path in _TEST_ROOT.glob("test_*.py")
        if path.name not in _ALLOWED_FILES
    )


def test_pytest_suite_does_not_run_full_live_generation_paths():
    """
    Routine pytest may check endpoints and mocked pipeline behavior, but must not
    invoke full DSPy/LM Studio generation against a real model.
    """
    violations: list[str] = []
    for path in _iter_test_python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                imported = {alias.name for alias in node.names}
                forbidden = sorted(imported & _FORBIDDEN_LIVE_GENERATION_NAMES)
                if forbidden:
                    violations.append(
                        f"{path.relative_to(_TEST_ROOT)} imports forbidden live-generation API(s): {', '.join(forbidden)}"
                    )
            elif isinstance(node, ast.Call):
                func = node.func
                name = None
                if isinstance(func, ast.Name):
                    name = func.id
                elif isinstance(func, ast.Attribute):
                    name = func.attr
                if name in _FORBIDDEN_LIVE_GENERATION_NAMES:
                    violations.append(
                        f"{path.relative_to(_TEST_ROOT)} calls forbidden live-generation API: {name}"
                    )

    assert violations == []
