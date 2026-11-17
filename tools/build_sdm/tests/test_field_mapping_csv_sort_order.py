"""Row sort-order test for FieldMappingCSVOutput."""

import csv
from pathlib import Path

from output_plugins.field_mapping_csv_output import (
    FieldMappingCSVOutput,
    FieldMappingCSVOutputConfig,
)
from tests.gim_config_helpers import build_field_schema, build_gim_config


def test_rows_sorted_by_event_type_code_then_status_then_field_name(tmp_path: Path) -> None:
    """Rows sort by gim_event_type_code, then required-before-optional, then field name.

    Required sorts before optional even when that contradicts alphabetical
    field-name order.
    """
    plugin = FieldMappingCSVOutput()

    gim_config = build_gim_config(
        category_code="05",
        category_name="sample",
        category_required=["zzz_field"],
        category_optional=["aaa_field"],
        subcat_name="first",
        event_type_codes={"00": "typeA", "01": "typeB"},
        field_schema={
            **build_field_schema("zzz", "field", description="zzz field", example_values="z"),
            **build_field_schema("aaa", "field", description="aaa field", example_values="a"),
        },
    )

    plugin_config = FieldMappingCSVOutputConfig(output_filename="test_output.csv")
    plugin.generate(gim_config, tmp_path, plugin_config)

    output_file = tmp_path / "test_output.csv"
    with output_file.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert [(row["gim_event_type_code"], row["Field Status"], row["Field Name"]) for row in rows] == [
        ("050000", "required", "zzz_field"),
        ("050000", "optional", "aaa_field"),
        ("050001", "required", "zzz_field"),
        ("050001", "optional", "aaa_field"),
    ]
