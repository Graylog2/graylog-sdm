"""Missing/invalid top-level field_schema key error test for FieldMappingCSVOutput."""

from pathlib import Path
from typing import Any

import pytest

from build_sdm.output_plugins.field_mapping_csv_output import FieldMappingCSVOutput


@pytest.mark.parametrize(
    "bad_config",
    [
        {"gim": {}},  # completely missing "field_schema"
        {"gim": {}, "field_schema": None},  # None instead of dict
        {"gim": {}, "field_schema": "not_a_dict"},  # wrong type
    ],
)
def test_missing_or_invalid_field_schema_key_raises(tmp_path: Path, bad_config: dict[str, Any]) -> None:
    """Raises ValueError when gim_config's top-level field_schema key is missing or invalid."""
    plugin = FieldMappingCSVOutput()
    with pytest.raises(
        ValueError,
        match='Missing or invalid top-level "field_schema" key in gim_config; expected dictionary.',
    ):
        plugin.generate(bad_config, tmp_path)
