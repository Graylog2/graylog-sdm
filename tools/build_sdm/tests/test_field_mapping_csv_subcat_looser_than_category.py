"""Subcategory-looser-than-category conflict test for FieldMappingCSVOutput."""

from pathlib import Path

import pytest

from output_plugins.field_mapping_csv_output import FieldMappingCSVOutput
from tests.gim_config_helpers import build_field_schema, build_gim_config


def test_subcategory_looser_than_category_raises(tmp_path: Path) -> None:
    """A subcategory cannot downgrade a field that is required at the category level."""
    plugin = FieldMappingCSVOutput()

    gim_config = build_gim_config(
        category_required=["user_domain"],
        subcat_optional=["user_domain"],
        field_schema=build_field_schema("user", "domain", description="User domain", example_values="CORP"),
    )

    with pytest.raises(ValueError, match="cannot loosen a category-level requirement"):
        plugin.generate(gim_config, tmp_path)
