"""Tests for build-sdm check-generated and the tree comparison behind it."""

import shutil
from pathlib import Path

import pytest

from build_sdm import cli
from build_sdm.check_generated import TreeDiff, compare_trees, format_diff


def _write(root: Path, files: dict[str, str]) -> Path:
    """Write files (relative path -> content) under root and return root."""
    for rel, content in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return root


def test_identical_trees_are_clean(tmp_path: Path) -> None:
    """Byte-identical trees produce no differences."""
    files = {"a.html": "A", "sub/b.html": "B"}
    committed = _write(tmp_path / "committed", files)
    fresh = _write(tmp_path / "fresh", files)

    assert compare_trees(committed, fresh).clean


def test_changed_stale_and_missing_are_reported(tmp_path: Path) -> None:
    """Differences are classified in both directions."""
    committed = _write(tmp_path / "committed", {"same.html": "S", "edited.html": "old", "gone.html": "G"})
    fresh = _write(tmp_path / "fresh", {"same.html": "S", "edited.html": "new", "sub/new.html": "N"})

    diff = compare_trees(committed, fresh)

    assert diff.changed == [Path("edited.html")]
    assert diff.stale == [Path("gone.html")]
    assert diff.missing == [Path("sub/new.html")]
    assert not diff.clean


def test_missing_committed_dir_reports_everything_missing(tmp_path: Path) -> None:
    """With nothing committed, every built file is missing."""
    fresh = _write(tmp_path / "fresh", {"a.html": "A"})

    assert compare_trees(tmp_path / "absent", fresh).missing == [Path("a.html")]


def test_format_diff_names_files_and_fix() -> None:
    """The report lists each kind of difference and tells the contributor how to fix it."""
    diff = TreeDiff(changed=[Path("a.html")], stale=[Path("old.html")], missing=[Path("b.html")])

    report = format_diff(diff, "generated/MadcapHtmlOutput")

    assert "changed" in report and "a.html" in report
    assert "stale" in report and "old.html" in report
    assert "missing" in report and "b.html" in report
    assert "  uv run build-sdm build\n" in report
    assert "  git rm -- generated/MadcapHtmlOutput/old.html\n" in report


def test_format_diff_never_suggests_clearing_the_directory() -> None:
    """The fix deletes only the listed stale files, never the whole output directory."""
    diff = TreeDiff(stale=[Path("old.html")])

    report = format_diff(diff, ".")

    assert "rm -rf" not in report
    assert "git rm -- ./old.html" in report


def test_format_diff_quotes_paths_for_the_shell() -> None:
    """Paths with spaces or quotes stay a single, literal shell argument."""
    diff = TreeDiff(stale=[Path("Graylog Information Models/it's.html")])

    report = format_diff(diff, "generated/Madcap")

    assert "git rm -- 'generated/Madcap/Graylog Information Models/it'\"'\"'s.html'" in report


def test_format_diff_omits_git_rm_without_stale_files() -> None:
    """With nothing stale, the fix is just rebuild and commit."""
    report = format_diff(TreeDiff(changed=[Path("a.html")]), "generated/MadcapHtmlOutput")

    assert "git rm" not in report


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    """Copy the package configs; MadCap's committed output is a temporary 'generated' dir."""
    config_dir = tmp_path / "configs"
    shutil.copytree(cli.DEFAULT_CONFIG_DIR, config_dir)
    (config_dir / "build_sdm.toml").write_text(
        f'[global]\nsdm_source_dir = "src/sdm"\noutput_dir = "{(tmp_path / "out").as_posix()}"\n',
        encoding="utf-8",
    )
    (config_dir / "madcap_html_output.toml").write_text(
        f'[plugin]\nname = "MadcapHtmlOutput"\nenabled = 1\n'
        f'output_dir = "{(tmp_path / "generated").as_posix()}"\n',
        encoding="utf-8",
    )
    return config_dir


@pytest.fixture
def generated(tmp_path: Path, config_dir: Path) -> Path:
    """Build once so the temporary 'generated' dir holds up-to-date MadCap output."""
    assert cli.main(["build", "-c", str(config_dir), "-ll", "error"]) == 0
    shutil.rmtree(tmp_path / "out")
    return tmp_path / "generated"


def _check(config_dir: Path) -> int:
    """Run check-generated against config_dir and return its exit code."""
    return cli.main(["check-generated", "-c", str(config_dir), "-ll", "error"])


def test_check_passes_on_clean_tree(tmp_path: Path, config_dir: Path, generated: Path) -> None:
    """Exit 0 when the committed output matches a fresh build; nothing is written outside a temp dir."""
    assert _check(config_dir) == 0
    assert not (tmp_path / "out").exists()


def test_check_fails_on_hand_edited_file(
    config_dir: Path, generated: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Exit 1 and name the file when a generated file was edited by hand."""
    page = sorted(generated.rglob("*.html"))[0]
    page.write_text(page.read_text(encoding="utf-8") + "<!-- edited -->", encoding="utf-8")

    assert _check(config_dir) == 1
    assert page.name in capsys.readouterr().out


def test_check_fails_on_stale_file(
    config_dir: Path, generated: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Exit 1 when generated/ holds a file the build no longer produces."""
    (generated / "removed_category.html").write_text("old", encoding="utf-8")

    assert _check(config_dir) == 1
    out = capsys.readouterr().out
    assert "stale" in out and "removed_category.html" in out


def test_check_fix_repeats_non_default_config_dir(
    config_dir: Path, generated: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The suggested rebuild uses the same config directory the check ran with."""
    (generated / "removed_category.html").write_text("old", encoding="utf-8")

    assert _check(config_dir) == 1
    assert f"uv run build-sdm build --config_dir {config_dir.resolve()}" in capsys.readouterr().out


def test_build_command_omits_default_config_dir(repo_root: Path) -> None:
    """With the package's own configs, the suggested rebuild is the plain build command."""
    assert cli._build_command(cli.DEFAULT_CONFIG_DIR, repo_root) == "uv run build-sdm build"


def test_check_fails_on_missing_file(
    config_dir: Path, generated: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Exit 1 when a file the build produces was not committed."""
    page = sorted(generated.rglob("*.html"))[0]
    page.unlink()

    assert _check(config_dir) == 1
    out = capsys.readouterr().out
    assert "missing" in out and page.name in out


def test_validate_placeholder_exits_2() -> None:
    """The validate command is not implemented yet and must not look like a passing check."""
    assert cli.main(["validate"]) == 2
