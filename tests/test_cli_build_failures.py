"""`build-sdm build` exits non-zero when a plugin fails (ADR 0002: plugin failures are fatal)."""

import shutil
from pathlib import Path

import pytest

from build_sdm import cli
from build_sdm.plugin_loader import safe_execute


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    """Copy the package configs, sending output to tmp_path and disabling MadCap for speed."""
    config_dir = tmp_path / "configs"
    shutil.copytree(cli.DEFAULT_CONFIG_DIR, config_dir)
    (config_dir / "build_sdm.toml").write_text(
        f'[global]\nsdm_source_dir = "src/sdm"\noutput_dir = "{(tmp_path / "out").as_posix()}"\n',
        encoding="utf-8",
    )
    (config_dir / "madcap_html_output.toml").write_text(
        '[plugin]\nname = "MadcapHtmlOutput"\nenabled = 0\n', encoding="utf-8"
    )
    return config_dir


def test_build_succeeds_with_valid_config(config_dir: Path) -> None:
    """A normal build exits 0."""
    assert cli.main(["build", "-c", str(config_dir), "-ll", "error"]) == 0


def test_plugin_write_failure_exits_1(config_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """An OSError while a plugin writes its output makes the build exit 1."""

    def failing_write_file(*_args: object, **_kwargs: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr("build_sdm.output_plugins.json_file_output.plugin.write_file", failing_write_file)

    assert cli.main(["build", "-c", str(config_dir), "-ll", "critical"]) == 1


def test_invalid_config_for_enabled_plugin_exits_1(config_dir: Path) -> None:
    """An enabled plugin whose config fails validation makes the build exit 1 instead of being skipped."""
    (config_dir / "json_file_output.toml").write_text(
        '[plugin]\nname = "JsonFileOutput"\nenabled = 1\njson_indent = "not a number"\n',
        encoding="utf-8",
    )

    assert cli.main(["build", "-c", str(config_dir), "-ll", "critical"]) == 1


def test_safe_execute_reraises() -> None:
    """safe_execute logs a plugin failure and re-raises it rather than swallowing it."""

    class Exploding:
        def generate(self) -> None:
            raise RuntimeError("boom")

    plugin = Exploding()
    # safe_execute is legacy code without annotations (see the mypy overrides).
    wrapped = safe_execute(Exploding.generate)  # type: ignore[no-untyped-call]

    with pytest.raises(RuntimeError, match="boom"):
        wrapped(plugin)
