"""Missing/empty event_type_codes error test for FieldMappingCSVOutput."""

from pathlib import Path

import pytest

from output_plugins.field_mapping_csv_output import FieldMappingCSVOutput
from tests.gim_config_helpers import build_field_schema, build_gim_config


def test_empty_event_type_codes_raises_instead_of_dropping_fields(tmp_path: Path) -> None:
    """A subcategory with fields but no event_type_codes must halt the build.

    Silently producing zero rows would hide the fact that this subcategory's
    field mappings are missing from the output entirely.
    """
    plugin = FieldMappingCSVOutput()

    gim_config = build_gim_config(
        subcat_required=["user_domain"],
        event_type_codes={},
        field_schema=build_field_schema("user", "domain", description="User domain", example_values="CORP"),
    )

    with pytest.raises(ValueError, match="event_type_codes"):
        plugin.generate(gim_config, tmp_path)
