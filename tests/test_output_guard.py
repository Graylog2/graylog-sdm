"""--madcap-output-dir refuses to overwrite a non-empty directory build-sdm didn't write (F4)."""

import os
import shutil
from pathlib import Path
from typing import Any

import pytest

from build_sdm import cli, runner
from build_sdm.utils.output_guard import (
    MARKER_NAME,
    UnsafeOutputDirError,
    check_output_dir,
    mark_output_dir,
    paths_overlap,
)


def test_missing_dir_is_safe_and_should_be_marked(tmp_path: Path) -> None:
    """A directory that doesn't exist yet is safe, and the build should mark it."""
    assert check_output_dir(tmp_path / "new") is True


def test_empty_dir_is_safe_and_should_be_marked(tmp_path: Path) -> None:
    """An empty directory is safe, and the build should mark it."""
    assert check_output_dir(tmp_path) is True


@pytest.mark.parametrize("name", [".DS_Store", "Thumbs.db", "desktop.ini"])
def test_dir_holding_only_os_metadata_counts_as_empty(tmp_path: Path, name: str) -> None:
    """OS metadata files (e.g. the .DS_Store Finder adds) don't make a directory non-empty."""
    (tmp_path / name).write_bytes(b"\x00")

    assert check_output_dir(tmp_path) is True


def test_os_metadata_does_not_hide_other_files(tmp_path: Path) -> None:
    """A directory with OS metadata and any other file is still refused."""
    (tmp_path / ".DS_Store").write_bytes(b"\x00")
    (tmp_path / "hand-written.htm").write_text("keep me", encoding="utf-8")

    with pytest.raises(UnsafeOutputDirError, match="--force"):
        check_output_dir(tmp_path)


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


def test_disabled_madcap_leaves_no_marker(tmp_path: Path, config_dir: Path) -> None:
    """With the MadCap plugin disabled, the build writes nothing to PATH, marker included."""
    madcap_config = config_dir / "madcap_html_output.toml"
    madcap_config.write_text(
        madcap_config.read_text(encoding="utf-8").replace("enabled = 1", "enabled = 0"),
        encoding="utf-8",
    )
    target = tmp_path / "new"

    assert _build(config_dir, target) == 0

    assert not (target / MARKER_NAME).exists()


def test_failure_before_generation_leaves_no_marker(tmp_path: Path, config_dir: Path) -> None:
    """A build that fails while loading the source never marks PATH."""
    (config_dir / "build_sdm.toml").write_text(
        f'[global]\nsdm_source_dir = "does/not/exist"\noutput_dir = "{(tmp_path / "out").as_posix()}"\n',
        encoding="utf-8",
    )
    target = tmp_path / "new"

    assert _build(config_dir, target) == 1

    assert not (target / MARKER_NAME).exists()


def test_path_under_a_file_fails_cleanly(tmp_path: Path, config_dir: Path) -> None:
    """A PATH whose parent is a regular file exits 1 instead of raising."""
    parent = tmp_path / "file"
    parent.write_text("x", encoding="utf-8")

    assert _build(config_dir, parent / "sub") == 1


@pytest.mark.skipif(os.geteuid() == 0, reason="root can list unreadable directories")
def test_unreadable_dir_fails_cleanly(tmp_path: Path, config_dir: Path) -> None:
    """A PATH the build can't list exits 1 instead of raising."""
    target = tmp_path / "locked"
    target.mkdir()
    target.chmod(0)
    try:
        assert _build(config_dir, target) == 1
    finally:
        target.chmod(0o755)


def _populate_while_loading(monkeypatch: pytest.MonkeyPatch, target: Path) -> None:
    """Make the source loader add a hand-written file to target, after the CLI's early check."""
    load = runner._load_and_transform_gim_config

    def load_then_populate(*args: Any, **kwargs: Any) -> Any:
        result = load(*args, **kwargs)
        target.mkdir(parents=True, exist_ok=True)
        (target / "hand-written.htm").write_text("keep me", encoding="utf-8")
        return result

    monkeypatch.setattr(runner, "_load_and_transform_gim_config", load_then_populate)


def test_dir_populated_after_check_is_refused(
    tmp_path: Path, config_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A PATH that gains unmarked files after the early check is refused before anything is written."""
    target = tmp_path / "new"
    _populate_while_loading(monkeypatch, target)

    assert _build(config_dir, target) == 1

    assert _snapshot(target) == {"hand-written.htm": b"keep me"}


def test_dir_populated_after_check_with_force_is_not_marked(
    tmp_path: Path, config_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With --force, a PATH that gains files after the early check is written but not marked."""
    target = tmp_path / "new"
    _populate_while_loading(monkeypatch, target)

    assert _build(config_dir, target, "--force") == 0

    assert list(target.rglob("*.html"))
    assert (target / "hand-written.htm").read_text(encoding="utf-8") == "keep me"
    assert not (target / MARKER_NAME).exists()


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        ("x", "x", True),
        ("x", "x/y", True),
        ("x/y", "x", True),
        ("x", "y", False),
        ("x/y", "x/z", False),
        ("x", "xy", False),
    ],
)
def test_paths_overlap(tmp_path: Path, a: str, b: str, expected: bool) -> None:
    """Paths overlap when equal or nested; siblings and shared name prefixes don't."""
    assert paths_overlap(tmp_path / a, tmp_path / b) is expected


@pytest.mark.parametrize("relation", ["contains", "equals", "inside"])
@pytest.mark.parametrize("force", [False, True])
def test_path_overlapping_build_output_is_refused_before_writing(
    tmp_path: Path, config_dir: Path, relation: str, force: bool
) -> None:
    """A PATH that contains, equals or sits inside the build's output dir exits 1, even with --force."""
    build_output = (tmp_path / "build" / "sdm_artifacts").as_posix()
    (config_dir / "build_sdm.toml").write_text(
        f'[global]\nsdm_source_dir = "src/sdm"\noutput_dir = "{build_output}"\n',
        encoding="utf-8",
    )
    target = {
        "contains": tmp_path / "build",
        "equals": tmp_path / "build" / "sdm_artifacts",
        "inside": tmp_path / "build" / "sdm_artifacts" / "madcap",
    }[relation]

    assert _build(config_dir, target, *(["--force"] if force else [])) == 1

    assert not (tmp_path / "build").exists()


def test_malformed_build_output_dir_fails_cleanly(tmp_path: Path, config_dir: Path) -> None:
    """A non-string global output_dir exits 1 instead of raising, and writes nothing to PATH."""
    (config_dir / "build_sdm.toml").write_text(
        '[global]\nsdm_source_dir = "src/sdm"\noutput_dir = 123\n', encoding="utf-8"
    )
    target = tmp_path / "new"

    assert _build(config_dir, target) == 1

    assert not target.exists()


def test_force_without_madcap_output_dir_is_an_error(config_dir: Path) -> None:
    """--force on its own is rejected rather than silently ignored."""
    assert cli.main(["build", "-c", str(config_dir), "-ll", "error", "--force"]) == 1
