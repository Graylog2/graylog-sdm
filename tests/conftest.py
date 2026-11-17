"""Shared pytest fixtures."""

from pathlib import Path

import pytest

from build_sdm.utils.paths import find_repo_root


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """Return the repository root, located via its build-sdm pyproject.toml."""
    return find_repo_root(Path(__file__).parent)


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add --update-golden, which rewrites the output snapshots in tests/golden/."""
    parser.addoption(
        "--update-golden",
        action="store_true",
        default=False,
        help="Rewrite tests/golden/ from the current build output instead of comparing against it.",
    )


@pytest.fixture
def update_golden(request: pytest.FixtureRequest) -> bool:
    """Return True when the run should rewrite the output snapshots."""
    return bool(request.config.getoption("--update-golden"))
