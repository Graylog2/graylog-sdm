"""Locate the graylog-sdm repository root."""

import tomllib
from pathlib import Path

__all__ = ["PROJECT_NAME", "RepoRootNotFoundError", "find_repo_root"]

PROJECT_NAME = "build-sdm"


class RepoRootNotFoundError(FileNotFoundError):
    """Raised when no ancestor directory holds the build-sdm pyproject.toml."""


def _is_repo_root(directory: Path) -> bool:
    """Return True if directory holds a pyproject.toml whose project name is build-sdm.

    Args:
        directory: Directory to check.

    Returns:
        True if directory is the repository root.
    """
    pyproject = directory / "pyproject.toml"
    if not pyproject.is_file():
        return False
    try:
        with pyproject.open("rb") as f:
            data = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError):
        return False
    return bool(data.get("project", {}).get("name") == PROJECT_NAME)


def _search_up(start: Path) -> Path | None:
    """Walk up from start and return the first repository root found.

    Args:
        start: Directory to start from; it is checked first.

    Returns:
        The repository root, or None if no ancestor qualifies.
    """
    for directory in (start, *start.parents):
        if _is_repo_root(directory):
            return directory
    return None


def find_repo_root(start: Path | None = None) -> Path:
    """Find the repository root without relying on a fixed directory depth.

    Walks up from start (default: the current working directory), then from this
    module's location, until it finds a pyproject.toml with name = "build-sdm".

    Args:
        start: Directory to search from first. Defaults to the current working directory.

    Returns:
        Absolute path of the repository root.

    Raises:
        RepoRootNotFoundError: If neither search finds the repository root.
    """
    first = (start or Path.cwd()).resolve()
    for origin in (first, Path(__file__).resolve().parent):
        root = _search_up(origin)
        if root is not None:
            return root
    raise RepoRootNotFoundError(
        f'No pyproject.toml with name = "{PROJECT_NAME}" found above {first} or {Path(__file__).parent}'
    )
