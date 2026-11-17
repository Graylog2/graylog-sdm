"""Build output must not depend on the order the filesystem lists source files in."""

from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from build_sdm.config_loader import load_gim_config_files
from build_sdm.runner import _load_and_transform_gim_config

FILE_NAMES = ["b.config.toml", "a.config.toml", "sub/c.config.toml"]


def _write_config_files(directory: Path) -> None:
    """Write minimal valid type = "config" files, each with a distinct top-level key.

    Args:
        directory: Directory to write the files into.
    """
    for name in FILE_NAMES:
        path = directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        key = path.name.split(".")[0]
        path.write_text(f'type = "config"\n\n[{key}_settings]\nvalue = "{key}"\n', encoding="utf-8")


def _rglob_returning(order: Callable[[list[Path]], list[Path]]) -> Callable[..., Iterator[Path]]:
    """Wrap Path.rglob so its results come back in a chosen order.

    Args:
        order: Function that reorders the real rglob results.

    Returns:
        A replacement for Path.rglob.
    """
    original = Path.rglob

    def rglob(self: Path, pattern: str, **kwargs: object) -> Iterator[Path]:
        return iter(order(list(original(self, pattern, **kwargs))))  # type: ignore[arg-type]

    return rglob


@pytest.mark.parametrize(
    "order",
    [lambda paths: paths, lambda paths: paths[::-1], lambda paths: sorted(paths, reverse=True)],
    ids=["filesystem", "reversed", "reverse-sorted"],
)
def test_files_load_in_sorted_path_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, order: Callable[[list[Path]], list[Path]]
) -> None:
    """Files are processed in sorted path order whatever order rglob returns them in."""
    _write_config_files(tmp_path)
    monkeypatch.setattr(Path, "rglob", _rglob_returning(order))

    result = load_gim_config_files(tmp_path, merge=False)

    assert list(result) == ["a.config.toml", "b.config.toml", "c.config.toml"]


def test_gim_dir_setting_is_repo_relative(tmp_path: Path) -> None:
    """The recorded source directory is the configured relative path, not an absolute one."""
    source_dir = tmp_path / "src" / "sdm"
    source_dir.mkdir(parents=True)
    _write_config_files(source_dir)

    result = _load_and_transform_gim_config(tmp_path, {"global": {"sdm_source_dir": "src/sdm"}})

    assert result["config"]["gim_dir"] == "src/sdm"
