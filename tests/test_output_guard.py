"""--madcap-output-dir refuses to overwrite a non-empty directory build-sdm didn't write (F4)."""

import shutil
from pathlib import Path

import pytest

from build_sdm import cli
from build_sdm.utils.output_guard import (
    MARKER_NAME,
    UnsafeOutputDirError,
    check_output_dir,
    mark_output_dir,
)


def test_missing_dir_is_safe_and_should_be_marked(tmp_path: Path) -> None:
    """A directory that doesn't exist yet is safe, and the build should mark it."""
    assert check_output_dir(tmp_path / "new") is True


def test_empty_dir_is_safe_and_should_be_marked(tmp_path: Path) -> None:
    """An empty directory is safe, and the build should mark it."""
    assert check_output_dir(tmp_path) is True


def test_marked_dir_is_safe(tmp_path: Path) -> None:
    """A directory holding the marker and earlier output is safe; it is already marked."""
    mark_output_dir(tmp_path)
    (tmp_path / "page.html").write_text("old", encoding="utf-8")

    assert check_output_dir(tmp_path) is False


def test_unmarked_non_empty_dir_is_refused(tmp_path: Path) -> None:
    """A non-empty directory without the marker is refused."""
    (tmp_path / "hand-written.htm").write_text("keep me", encoding="utf-8")

    with pytest.raises(UnsafeOutputDirError, match="--force"):
        check_output_dir(tmp_path)


def test_force_allows_unmarked_dir_without_marking_it(tmp_path: Path) -> None:
    """With force, an unmarked non-empty directory is allowed but not marked."""
    (tmp_path / "hand-written.htm").write_text("keep me", encoding="utf-8")

    assert check_output_dir(tmp_path, force=True) is False


def test_file_in_place_of_dir_is_refused(tmp_path: Path) -> None:
    """A file at the output path is refused, even with force."""
    target = tmp_path / "file"
    target.write_text("x", encoding="utf-8")

    with pytest.raises(UnsafeOutputDirError, match="not a directory"):
        check_output_dir(target, force=True)


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    """Copy the package configs, sending the other plugins' output to tmp_path."""
    config_dir = tmp_path / "configs"
    shutil.copytree(cli.DEFAULT_CONFIG_DIR, config_dir)
    (config_dir / "build_sdm.toml").write_text(
        f'[global]\nsdm_source_dir = "src/sdm"\noutput_dir = "{(tmp_path / "out").as_posix()}"\n',
        encoding="utf-8",
    )
    return config_dir


def _build(config_dir: Path, target: Path, *extra: str) -> int:
    """Run build with --madcap-output-dir target and return the exit code."""
    return cli.main(
        ["build", "-c", str(config_dir), "-ll", "error", "--madcap-output-dir", str(target), *extra]
    )


def _snapshot(directory: Path) -> dict[str, bytes]:
    """Return every file under directory, keyed by relative path."""
    return {str(p.relative_to(directory)): p.read_bytes() for p in directory.rglob("*") if p.is_file()}


def test_build_refuses_unmarked_dir_and_changes_nothing(tmp_path: Path, config_dir: Path) -> None:
    """Pointed at a non-empty unmarked directory, build exits 1 and leaves it untouched."""
    target = tmp_path / "flare"
    target.mkdir()
    (target / "hand-written.htm").write_text("keep me", encoding="utf-8")
    before = _snapshot(target)

    assert _build(config_dir, target) == 1

    assert _snapshot(target) == before


def test_build_marks_new_dir_and_rebuilds_into_it(tmp_path: Path, config_dir: Path) -> None:
    """A new directory is marked on the first build, so a second build needs no --force."""
    target = tmp_path / "new"

    assert _build(config_dir, target) == 0
    assert (target / MARKER_NAME).is_file()
    assert list(target.rglob("*.html"))

    assert _build(config_dir, target) == 0


def test_build_force_writes_without_marking(tmp_path: Path, config_dir: Path) -> None:
    """--force writes into an unmarked directory, keeps unrelated files, and adds no marker."""
    target = tmp_path / "flare"
    target.mkdir()
    (target / "hand-written.htm").write_text("keep me", encoding="utf-8")

    assert _build(config_dir, target, "--force") == 0

    assert list(target.rglob("*.html"))
    assert (target / "hand-written.htm").read_text(encoding="utf-8") == "keep me"
    assert not (target / MARKER_NAME).exists()


def test_dry_run_checks_but_writes_no_marker(tmp_path: Path, config_dir: Path) -> None:
    """--dry-run still refuses an unsafe directory, and creates nothing for a safe one."""
    unsafe = tmp_path / "flare"
    unsafe.mkdir()
    (unsafe / "hand-written.htm").write_text("keep me", encoding="utf-8")
    safe = tmp_path / "new"

    assert _build(config_dir, unsafe, "--dry-run") == 1
    assert _build(config_dir, safe, "--dry-run") == 0
    assert not safe.exists()


def test_force_without_madcap_output_dir_is_an_error(config_dir: Path) -> None:
    """--force on its own is rejected rather than silently ignored."""
    assert cli.main(["build", "-c", str(config_dir), "-ll", "error", "--force"]) == 1
