"""CSV quoting round-trip test for FieldMappingCSVOutput."""

import csv
from pathlib import Path

from build_sdm.output_plugins.field_mapping_csv_output import (
    FieldMappingCSVOutput,
    FieldMappingCSVOutputConfig,
)
from tests.gim_config_helpers import build_field_schema, build_gim_config


def test_description_and_example_with_commas_round_trip_correctly(tmp_path: Path) -> None:
    """Values with commas/quotes are escaped by csv.writer and recoverable via csv.reader."""
    plugin = FieldMappingCSVOutput()

    gim_config = build_gim_config(
        category_required=["user_domain"],
        field_schema=build_field_schema(
            "user",
            "domain",
            description='The domain, e.g. "CORP", of the user',
            example_values="CORP, EXAMPLE",
        ),
    )

    plugin_config = FieldMappingCSVOutputConfig(output_filename="test_output.csv")
    plugin.generate(gim_config, tmp_path, plugin_config)

    output_file = tmp_path / "test_output.csv"
    with output_file.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert len(rows) == 1
    assert rows[0]["Field Description"] == 'The domain, e.g. "CORP", of the user'
    assert rows[0]["Field Example"] == "CORP, EXAMPLE"
