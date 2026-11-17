"""The category authoring template produces a category that loads and builds."""

import importlib
import json
import pkgutil
from pathlib import Path
from typing import Any

import pytest

from build_sdm import output_plugins
from build_sdm.config_loader import load_gim_config_files
from build_sdm.output_plugins.message_summaries_output import MessageSummariesOutput
from build_sdm.utils.serialization import to_serializable
from build_sdm.utils.transform import restructure_gim_config


@pytest.fixture
def category_dir(repo_root: Path, tmp_path: Path) -> Path:
    """Write the template, with its placeholders filled in, to a temporary source directory."""
    template = (repo_root / "docs" / "templates" / "category.toml.template").read_text(encoding="utf-8")
    filled = template.replace("category_name", "example_category").replace("code = XX", "code = 98")
    source_dir = tmp_path / "src"
    source_dir.mkdir()
    (source_dir / "98.example_category.toml").write_text(filled, encoding="utf-8")
    return source_dir


def _load(source_dir: Path) -> dict[str, Any]:
    """Load, serialize and restructure a source directory the way the build does.

    Args:
        source_dir: Directory of SDM source TOML files.

    Returns:
        The restructured gim_config.
    """
    for _, name, _ in pkgutil.walk_packages(output_plugins.__path__, output_plugins.__name__ + "."):
        importlib.import_module(name)
    return restructure_gim_config(to_serializable(load_gim_config_files(source_dir, merge=False)))


def test_template_category_loads(category_dir: Path) -> None:
    """A category created from the template passes GIMCategory validation."""
    gim_config = _load(category_dir)

    category = gim_config["gim"]["example_category"]
    assert category["name"] == "example_category"
    assert category["code"] == "98"


def test_template_category_builds_message_summaries(category_dir: Path, tmp_path: Path) -> None:
    """A category created from the template passes message-summary generation."""
    gim_config = _load(category_dir)
    output_dir = tmp_path / "out"
    output_dir.mkdir()

    # The plugin class is legacy code without annotations (see the mypy overrides).
    MessageSummariesOutput().generate(gim_config, output_dir)  # type: ignore[no-untyped-call]

    summaries = json.loads((output_dir / "message_summaries.json").read_text(encoding="utf-8"))
    assert summaries
