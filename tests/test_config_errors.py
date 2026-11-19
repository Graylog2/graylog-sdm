"""Broken configuration stops a command instead of falling back to defaults or dropping files."""

import shutil
from pathlib import Path

import pytest

from build_sdm import cli
from build_sdm.config_loader import load_gim_config_files, load_script_config_files

BROKEN_TOML = "[global\nsdm_source_dir = "


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    """Copy the package configs to a temporary directory."""
    config_dir = tmp_path / "configs"
    shutil.copytree(cli.DEFAULT_CONFIG_DIR, config_dir)
    return config_dir


def test_malformed_script_config_raises(config_dir: Path) -> None:
    """A file that doesn't parse is an error naming the file, not an empty config."""
    (config_dir / "broken.toml").write_text(BROKEN_TOML, encoding="utf-8")

    with pytest.raises(ValueError, match=r"Unable to load script configuration file .*broken\.toml"):
        load_script_config_files(config_dir)


def test_plugin_table_without_name_raises(config_dir: Path) -> None:
    """A [plugin] table must name its plugin."""
    (config_dir / "nameless.toml").write_text("[plugin]\nenabled = 1\n", encoding="utf-8")

    with pytest.raises(ValueError, match=r"nameless\.toml"):
        load_script_config_files(config_dir)


@pytest.mark.parametrize("command", ["build", "check-generated", "validate"])
def test_commands_fail_on_malformed_script_config(
    config_dir: Path, command: str, caplog: pytest.LogCaptureFixture, capsys: pytest.CaptureFixture[str]
) -> None:
    """Every command exits 1 and names the broken file; validate never checks a default tree instead."""
    (config_dir / "broken.toml").write_text(BROKEN_TOML, encoding="utf-8")

    assert cli.main([command, "-c", str(config_dir), "-ll", "error"]) == 1
    assert "broken.toml" in caplog.text
    assert "error(s)" not in capsys.readouterr().out


def test_duplicate_source_file_names_are_rejected(tmp_path: Path) -> None:
    """Two source files with the same name in different directories can't silently replace each other."""
    for sub in ("a", "b"):
        path = tmp_path / sub / "dup.config.toml"
        path.parent.mkdir()
        path.write_text('type = "config"\n', encoding="utf-8")

    expected = (
        r"dup\.config\.toml: file name is used more than once: a/dup\.config\.toml, b/dup\.config\.toml"
    )
    with pytest.raises(ValueError, match=expected):
        load_gim_config_files(tmp_path, merge=False)
