"""Unchecked-fields exemption test for FieldMappingCSVOutput."""

import csv
from pathlib import Path

from output_plugins.field_mapping_csv_output import (
    FieldMappingCSVOutput,
    FieldMappingCSVOutputConfig,
)
from tests.gim_config_helpers import build_gim_config


def test_unchecked_field_with_no_schema_match_gets_blank_metadata(tmp_path: Path) -> None:
    """A field listed in unchecked_fields skips the field_schema match requirement.

    Its row is still emitted, with blank Description/Data Type/Example instead
    of raising.
    """
    plugin = FieldMappingCSVOutput()

    gim_config = build_gim_config(
        category_code="22",
        category_name="audit",
        category_required=["source"],
        subcat_name="default",
        event_type_codes={"00": "audit message"},
    )

    plugin_config = FieldMappingCSVOutputConfig(
        output_filename="test_output.csv", unchecked_fields=["source"]
    )
    plugin.generate(gim_config, tmp_path, plugin_config)

    output_file = tmp_path / "test_output.csv"
    with output_file.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert len(rows) == 1
    assert rows[0]["Field Name"] == "source"
    assert rows[0]["Field Status"] == "required"
    assert rows[0]["Field Description"] == ""
    assert rows[0]["Field Data Type"] == ""
    assert rows[0]["Field Example"] == ""
