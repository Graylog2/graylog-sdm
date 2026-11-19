"""CategoryDataCSVOutput fails the build instead of writing an incomplete or missing CSV."""

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from build_sdm.output_plugins.category_data_csv_output import CategoryDataCSVOutput


def _gim_config(subcategories: dict[str, Any]) -> dict[str, Any]:
    """Build a gim_config with one 'authentication' category.

    Args:
        subcategories: The category's subcategories.

    Returns:
        A minimal gim_config.
    """
    return {
        "gim": {"authentication": {"code": "00", "name": "Authentication", "subcategories": subcategories}}
    }


@pytest.fixture
def plugin() -> CategoryDataCSVOutput:
    """Return a fresh plugin instance."""
    # The plugin is legacy code without annotations (see the mypy overrides).
    return CategoryDataCSVOutput()  # type: ignore[no-untyped-call]


VALID_SUBCATEGORIES = {"01": {"name": "logon", "event_type_codes": {"00": {"name": "logon_success"}}}}


def test_category_without_lookup_lines_raises(tmp_path: Path, plugin: CategoryDataCSVOutput) -> None:
    """A category that yields no lookup lines is an error, and no CSV is written."""
    with pytest.raises(RuntimeError, match="Unable to generate lookup data for category authentication"):
        plugin.generate(_gim_config({}), tmp_path)

    assert not (tmp_path / "category_data.csv").exists()


def test_write_failure_propagates(tmp_path: Path, plugin: CategoryDataCSVOutput) -> None:
    """An OSError from write_file propagates instead of being logged and swallowed."""
    with (
        patch(
            "build_sdm.output_plugins.category_data_csv_output.plugin.write_file",
            side_effect=OSError("disk full"),
        ),
        pytest.raises(OSError, match="disk full"),
    ):
        plugin.generate(_gim_config(VALID_SUBCATEGORIES), tmp_path)
