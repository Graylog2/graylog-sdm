"""Tests for find_repo_root: where every build-sdm command reads and writes."""

from pathlib import Path

import pytest

from build_sdm.utils import paths
from build_sdm.utils.paths import RepoRootNotFoundError, find_repo_root


def _pyproject(directory: Path, name: str) -> Path:
    """Write a pyproject.toml with the given project name and return its directory."""
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "pyproject.toml").write_text(f'[project]\nname = "{name}"\n', encoding="utf-8")
    return directory


@pytest.fixture
def no_module_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Point the module-location fallback at a tree with no build-sdm pyproject.toml."""
    monkeypatch.setattr(paths, "__file__", str(tmp_path / "elsewhere" / "pkg" / "paths.py"))


@pytest.mark.usefixtures("no_module_fallback")
def test_start_directory_itself_can_be_the_root(tmp_path: Path) -> None:
    """The start directory is checked first."""
    root = _pyproject(tmp_path / "repo", paths.PROJECT_NAME)

    assert find_repo_root(root) == root.resolve()


@pytest.mark.usefixtures("no_module_fallback")
def test_walks_up_to_nearest_matching_ancestor(tmp_path: Path) -> None:
    """From a nested directory, the nearest ancestor with the build-sdm pyproject.toml wins."""
    _pyproject(tmp_path / "outer", paths.PROJECT_NAME)
    inner = _pyproject(tmp_path / "outer" / "inner", paths.PROJECT_NAME)
    start = inner / "src" / "sdm"
    start.mkdir(parents=True)

    assert find_repo_root(start) == inner.resolve()


@pytest.mark.usefixtures("no_module_fallback")
def test_skips_pyproject_with_other_name(tmp_path: Path) -> None:
    """A pyproject.toml for another project is not the repository root."""
    root = _pyproject(tmp_path / "repo", paths.PROJECT_NAME)
    other = _pyproject(root / "vendored", "something-else")

    assert find_repo_root(other) == root.resolve()


@pytest.mark.usefixtures("no_module_fallback")
def test_skips_unparseable_pyproject(tmp_path: Path) -> None:
    """A malformed pyproject.toml on the way up is ignored, not fatal."""
    root = _pyproject(tmp_path / "repo", paths.PROJECT_NAME)
    broken = root / "broken"
    broken.mkdir()
    (broken / "pyproject.toml").write_text("[project\nname = ", encoding="utf-8")

    assert find_repo_root(broken) == root.resolve()


def test_falls_back_to_module_location(tmp_path: Path, repo_root: Path) -> None:
    """When the start tree has no build-sdm pyproject.toml, the package's own location is used."""
    unrelated = _pyproject(tmp_path / "unrelated", "something-else")

    assert find_repo_root(unrelated) == repo_root


@pytest.mark.usefixtures("no_module_fallback")
def test_raises_when_no_root_found(tmp_path: Path) -> None:
    """With no match from the start directory or the module location, a clear error is raised."""
    unrelated = _pyproject(tmp_path / "unrelated", "something-else")

    with pytest.raises(RepoRootNotFoundError, match='name = "build-sdm"'):
        find_repo_root(unrelated)


def test_defaults_to_current_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Without a start argument, the search begins in the current working directory."""
    root = _pyproject(tmp_path / "repo", paths.PROJECT_NAME)
    monkeypatch.chdir(root)
    monkeypatch.setattr(paths, "__file__", str(tmp_path / "elsewhere" / "paths.py"))

    assert find_repo_root() == root.resolve()
