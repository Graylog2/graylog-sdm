"""Subcategory-stricter-than-category conflict test for FieldMappingCSVOutput."""

import csv
from pathlib import Path

from build_sdm.output_plugins.field_mapping_csv_output import (
    FieldMappingCSVOutput,
    FieldMappingCSVOutputConfig,
)
from tests.gim_config_helpers import build_field_schema, build_gim_config


def test_subcategory_stricter_than_category_emits_two_rows(tmp_path: Path) -> None:
    """A field optional at category but required at subcategory is valid.

    It must appear as two separate rows with different statuses.
    """
    plugin = FieldMappingCSVOutput()

    gim_config = build_gim_config(
        category_optional=["user_domain"],
        subcat_required=["user_domain"],
        field_schema=build_field_schema("user", "domain", description="User domain", example_values="CORP"),
    )

    plugin_config = FieldMappingCSVOutputConfig(output_filename="test_output.csv")
    plugin.generate(gim_config, tmp_path, plugin_config)

    output_file = tmp_path / "test_output.csv"
    with output_file.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert len(rows) == 2
    assert [row["Field Name"] for row in rows] == ["user_domain", "user_domain"]
    assert [row["Field Status"] for row in rows] == ["required", "optional"]
