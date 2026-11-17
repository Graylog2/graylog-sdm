"""Same-status dedup test for FieldMappingCSVOutput."""

import csv
from pathlib import Path
from typing import Any

from output_plugins.field_mapping_csv_output import (
    FieldMappingCSVOutput,
    FieldMappingCSVOutputConfig,
)
from tests.gim_config_helpers import build_field_schema, build_gim_config


def _minimal_config(
    category_field_tier: str, subcat_field_tier: str, field_name: str = "user_name"
) -> dict[str, Any]:
    """Build a minimal gim_config with one field at the given category/subcategory tiers."""
    category_fields = {category_field_tier: [field_name]}
    subcat_fields = {subcat_field_tier: [field_name]}
    return build_gim_config(
        category_required=category_fields.get("required"),
        category_recommended=category_fields.get("recommended"),
        category_optional=category_fields.get("optional"),
        subcat_required=subcat_fields.get("required"),
        subcat_recommended=subcat_fields.get("recommended"),
        subcat_optional=subcat_fields.get("optional"),
        field_schema=build_field_schema("user", "name", description="User name", example_values="admin"),
    )


def test_same_status_at_category_and_subcategory_emits_one_row(tmp_path: Path) -> None:
    """A field required at both category and subcategory level produces a single row."""
    plugin = FieldMappingCSVOutput()
    gim_config = _minimal_config("required", "required")

    plugin_config = FieldMappingCSVOutputConfig(output_filename="test_output.csv")
    plugin.generate(gim_config, tmp_path, plugin_config)

    output_file = tmp_path / "test_output.csv"
    with output_file.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert len(rows) == 1
    assert rows[0]["Field Name"] == "user_name"
    assert rows[0]["Field Status"] == "required"
