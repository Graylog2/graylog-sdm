"""Plugin output directory precedence: CLI override > plugin config > <output_dir>/<Plugin>/."""

import shutil
from pathlib import Path

import pytest

from build_sdm import cli
from build_sdm.output_plugins.field_mapping_csv_output import FieldMappingCSVOutput
from build_sdm.output_plugins.madcap_html_output import MadcapHtmlOutput, MadcapHtmlOutputConfig
from build_sdm.runner import _plugin_output_dir


@pytest.fixture
def default_dir(tmp_path: Path) -> Path:
    """Return the runner's default per-plugin directory for MadcapHtmlOutput."""
    return tmp_path / "build" / "sdm_artifacts" / "MadcapHtmlOutput"


def test_madcap_uses_default_without_config(tmp_path: Path, default_dir: Path) -> None:
    """With no output_dir configured, MadCap writes to the runner's default directory."""
    plugin = MadcapHtmlOutput()

    assert plugin.resolve_output_dir(default_dir, tmp_path, MadcapHtmlOutputConfig()) == default_dir


def test_madcap_config_relative_path_resolves_against_repo_root(tmp_path: Path, default_dir: Path) -> None:
    """A relative configured output_dir resolves against the repository root, not the cwd."""
    plugin = MadcapHtmlOutput()
    config = MadcapHtmlOutputConfig(output_dir="generated/MadcapHtmlOutput")

    assert plugin.resolve_output_dir(default_dir, tmp_path, config) == tmp_path / "generated/MadcapHtmlOutput"


def test_madcap_config_absolute_path_is_used_as_is(tmp_path: Path, default_dir: Path) -> None:
    """An absolute configured output_dir is used unchanged."""
    target = tmp_path / "elsewhere"
    config = MadcapHtmlOutputConfig(output_dir=str(target))

    assert MadcapHtmlOutput().resolve_output_dir(default_dir, tmp_path, config) == target


def test_cli_override_beats_config(tmp_path: Path) -> None:
    """An override (from --madcap-output-dir) wins over the plugin's configured output_dir."""
    config = MadcapHtmlOutputConfig(output_dir="generated/MadcapHtmlOutput")
    override = tmp_path / "flag"

    result = _plugin_output_dir(
        MadcapHtmlOutput(), config, tmp_path / "out", tmp_path, {"MadcapHtmlOutput": override}
    )

    assert result == override


def test_override_applies_only_to_its_plugin(tmp_path: Path) -> None:
    """An override keyed to MadcapHtmlOutput leaves other plugins on their default directory."""
    result = _plugin_output_dir(
        FieldMappingCSVOutput(), None, tmp_path / "out", tmp_path, {"MadcapHtmlOutput": tmp_path / "flag"}
    )

    assert result == tmp_path / "out" / "FieldMappingCSVOutput"


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    """Copy the package configs; build output to tmp_path, MadCap to a configured tmp location."""
    config_dir = tmp_path / "configs"
    shutil.copytree(cli.DEFAULT_CONFIG_DIR, config_dir)
    (config_dir / "build_sdm.toml").write_text(
        f'[global]\nsdm_source_dir = "src/sdm"\noutput_dir = "{(tmp_path / "out").as_posix()}"\n',
        encoding="utf-8",
    )
    (config_dir / "madcap_html_output.toml").write_text(
        f'[plugin]\nname = "MadcapHtmlOutput"\nenabled = 1\n'
        f'output_dir = "{(tmp_path / "configured").as_posix()}"\n',
        encoding="utf-8",
    )
    return config_dir


def _html_files(directory: Path) -> list[Path]:
    """Return the HTML files under directory."""
    return sorted(directory.rglob("*.html"))


def test_build_writes_madcap_only_to_configured_dir(tmp_path: Path, config_dir: Path) -> None:
    """Without the flag, MadCap output goes only to the configured directory."""
    assert cli.main(["build", "-c", str(config_dir), "-ll", "error"]) == 0

    assert _html_files(tmp_path / "configured")
    assert not (tmp_path / "out" / "MadcapHtmlOutput").exists()


def test_build_flag_replaces_configured_dir(
    tmp_path: Path, config_dir: Path, monkeypatch: pytest.MonkeyPatch, repo_root: Path
) -> None:
    """--madcap-output-dir writes only there; a relative flag resolves against the cwd."""
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(work)
    generated = repo_root / "generated" / "MadcapHtmlOutput"
    before = sorted(p.stat().st_mtime_ns for p in generated.rglob("*")) if generated.exists() else []

    assert cli.main(["build", "-c", str(config_dir), "-ll", "error", "--madcap-output-dir", "x"]) == 0

    assert _html_files(work / "x")
    assert not (tmp_path / "configured").exists()
    assert not (tmp_path / "out" / "MadcapHtmlOutput").exists()
    after = sorted(p.stat().st_mtime_ns for p in generated.rglob("*")) if generated.exists() else []
    assert after == before
