import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--run-packaging",
        action="store_true",
        default=False,
        help="run slow package install smoke tests marked with @pytest.mark.packaging",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-packaging"):
        return

    skip_packaging = pytest.mark.skip(
        reason="slow package install smoke test; use --run-packaging -m packaging to run",
    )
    for item in items:
        if "packaging" in item.keywords:
            item.add_marker(skip_packaging)
