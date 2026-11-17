"""Missing field_schema entry error test for FieldMappingCSVOutput."""

from pathlib import Path

import pytest

from build_sdm.output_plugins.field_mapping_csv_output import FieldMappingCSVOutput
from tests.gim_config_helpers import build_field_schema, build_gim_config


def test_field_with_no_matching_field_schema_entry_raises(tmp_path: Path) -> None:
    """A field with no entity_field_suffix match in field_schema halts the build.

    This prevents silently dropping data rather than reporting it.
    """
    plugin = FieldMappingCSVOutput()

    gim_config = build_gim_config(
        category_required=["nonexistent_field"],
        field_schema=build_field_schema("user", "domain", description="User domain", example_values="CORP"),
    )

    with pytest.raises(ValueError, match="no matching field_schema entry"):
        plugin.generate(gim_config, tmp_path)
