"""Invalid per-category or per-entity MadCap config fails generation (ADR 0002: plugin failures are fatal)."""

from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from build_sdm.output_plugins.madcap_html_output import MadcapHtmlOutput
from build_sdm.runner import _load_and_transform_gim_config


@pytest.fixture
def gim_config(repo_root: Path) -> dict[str, Any]:
    """Load the real SDM source, as the build does."""
    return _load_and_transform_gim_config(repo_root, {"global": {"sdm_source_dir": "src/sdm"}})


@pytest.mark.parametrize("section", ["gim", "field_schema"])
def test_invalid_config_fails_generation(tmp_path: Path, gim_config: dict[str, Any], section: str) -> None:
    """A config block that fails validation stops generation instead of being skipped."""
    plugin = MadcapHtmlOutput()
    name = sorted(gim_config[section])[0]
    meta = gim_config[section][name].setdefault("meta", {})
    meta.setdefault("plugin_config", {})[plugin.plugin_name] = {"category_template_filename": 123}

    with pytest.raises(RuntimeError, match="Failed during GIM category page generation") as excinfo:
        plugin.generate(gim_config, tmp_path)

    assert isinstance(excinfo.value.__cause__, ValidationError)
