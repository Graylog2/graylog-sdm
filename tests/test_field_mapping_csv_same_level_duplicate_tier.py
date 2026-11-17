"""Same-level duplicate-tier conflict test for FieldMappingCSVOutput."""

from pathlib import Path

import pytest

from build_sdm.output_plugins.field_mapping_csv_output import FieldMappingCSVOutput
from tests.gim_config_helpers import build_field_schema, build_gim_config


def test_field_in_two_tiers_at_same_level_raises(tmp_path: Path) -> None:
    """Listing one field in two tiers of the same level is ambiguous.

    E.g. both required_fields and recommended_fields of the same category
    must halt the build.
    """
    plugin = FieldMappingCSVOutput()

    gim_config = build_gim_config(
        category_required=["user_domain"],
        category_recommended=["user_domain"],
        field_schema=build_field_schema("user", "domain", description="User domain", example_values="CORP"),
    )

    with pytest.raises(ValueError, match="listed in more than one tier"):
        plugin.generate(gim_config, tmp_path)
