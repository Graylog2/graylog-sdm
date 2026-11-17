"""Shared pytest fixtures."""

from pathlib import Path

import pytest

from build_sdm.utils.paths import find_repo_root


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """Return the repository root, located via its build-sdm pyproject.toml."""
    return find_repo_root(Path(__file__).parent)
