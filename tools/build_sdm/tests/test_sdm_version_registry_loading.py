"""Tests for loading the sdm_version registry via the GIM config pipeline."""

import importlib
import pkgutil
from pathlib import Path

import output_plugins
from config_loader import load_gim_config_files
from utils.serialization import to_serializable
from utils.transform import restructure_gim_config


def _ensure_plugins_imported() -> None:
    """Import every output_plugins submodule so plugin_name lookups resolve."""
    for _, name, _ in pkgutil.walk_packages(output_plugins.__path__, output_plugins.__name__ + "."):
        importlib.import_module(name)


def test_sdm_version_registry_loads_from_isolated_config_file(tmp_path: Path) -> None:
    """A standalone type=config file declaring a top-level sdm_version block.

    Merges into the final structured config under config.sdm_version.
    """
    gim_dir = tmp_path / "_meta" / "gim"
    gim_dir.mkdir(parents=True)
    (gim_dir / "sdm_version.config.toml").write_text(
        'type = "config"\n\n'
        '[sdm_version]\n'
        'current_version = "7.1.0"\n'
    )

    gim_config = load_gim_config_files(gim_dir, merge=False)
    serialized = to_serializable(gim_config)
    structured = restructure_gim_config(serialized)

    assert structured["config"]["sdm_version"]["current_version"] == "7.1.0"


def test_real_sdm_version_config_file_loads_correctly() -> None:
    """The actual repo _meta/gim/sdm_version.config.toml parses and merges correctly.

    Merges alongside the rest of the real GIM config tree.
    """
    _ensure_plugins_imported()
    repo_gim_dir = Path(__file__).resolve().parents[3] / "_meta" / "gim"

    gim_config = load_gim_config_files(repo_gim_dir, merge=False)
    serialized = to_serializable(gim_config)
    structured = restructure_gim_config(serialized)

    assert structured["config"]["sdm_version"]["current_version"] == "7.1.0"
