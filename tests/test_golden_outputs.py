"""Snapshot tests: the build's plugin output from the live src/sdm data matches tests/golden/.

Any change to the data or the tool that changes this output must update the snapshots in
the same commit, so the change shows up in review:

    uv run pytest tests/test_golden_outputs.py --update-golden

MadcapHtmlOutput is not snapshotted here; generated/ and `build-sdm check-generated`
cover it.
"""

import shutil
from pathlib import Path

import pytest

from build_sdm.cli import DEFAULT_CONFIG_DIR
from build_sdm.runner import run_build

SNAPSHOT_PLUGINS = [
    "CategoryDataCSVOutput",
    "FieldMappingCSVOutput",
    "JsonFileOutput",
    "MessageSummariesOutput",
]


def _files(directory: Path) -> set[Path]:
    """Return every file under directory, relative to it.

    Args:
        directory: Directory to list.

    Returns:
        Relative paths of all files, or an empty set if directory doesn't exist.
    """
    if not directory.is_dir():
        return set()
    return {p.relative_to(directory) for p in directory.rglob("*") if p.is_file()}


@pytest.fixture(scope="module")
def build_output(repo_root: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build the live data once, with MadCap disabled, into a temporary directory.

    The package's configs are copied so the output directory can point outside the
    repository; the source directory stays repo-relative, as in a normal build.
    """
    tmp = tmp_path_factory.mktemp("golden")
    config_dir = tmp / "configs"
    shutil.copytree(DEFAULT_CONFIG_DIR, config_dir)
    output_dir = tmp / "out"
    (config_dir / "build_sdm.toml").write_text(
        f'[global]\nsdm_source_dir = "src/sdm"\noutput_dir = "{output_dir.as_posix()}"\n',
        encoding="utf-8",
    )
    (config_dir / "madcap_html_output.toml").write_text(
        '[plugin]\nname = "MadcapHtmlOutput"\nenabled = 0\n', encoding="utf-8"
    )

    run_build(repo_root, config_dir)
    return output_dir


@pytest.mark.parametrize("plugin", SNAPSHOT_PLUGINS)
def test_plugin_output_matches_snapshot(
    plugin: str, build_output: Path, repo_root: Path, update_golden: bool
) -> None:
    """Each plugin's output matches its snapshot: no changed, missing or extra files."""
    actual_dir = build_output / plugin
    golden_dir = repo_root / "tests" / "golden" / plugin

    if update_golden:
        shutil.rmtree(golden_dir, ignore_errors=True)
        shutil.copytree(actual_dir, golden_dir)
        return

    actual, golden = _files(actual_dir), _files(golden_dir)
    assert actual, f"{plugin} produced no output"
    assert not golden - actual, f"{plugin}: snapshot files no longer produced: {sorted(golden - actual)}"
    assert not actual - golden, f"{plugin}: new files without a snapshot: {sorted(actual - golden)}"
    changed = sorted(
        str(rel) for rel in actual if (actual_dir / rel).read_bytes() != (golden_dir / rel).read_bytes()
    )
    assert not changed, (
        f"{plugin}: output differs from snapshot in {changed}. If the change is intended, run "
        "`uv run pytest tests/test_golden_outputs.py --update-golden` and commit tests/golden/."
    )
