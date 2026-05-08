from __future__ import annotations

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-packaging",
        action="store_true",
        default=False,
        help="Run slow package-install smoke tests marked with @pytest.mark.packaging.",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if config.getoption("--run-packaging"):
        return

    skip_packaging = pytest.mark.skip(
        reason="package-install smoke test; pass --run-packaging and select -m packaging to run"
    )
    for item in items:
        if "packaging" in item.keywords:
            item.add_marker(skip_packaging)
