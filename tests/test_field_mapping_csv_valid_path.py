"""Happy-path test for FieldMappingCSVOutput."""

import csv
from pathlib import Path

from build_sdm.output_plugins.field_mapping_csv_output import (
    FieldMappingCSVOutput,
    FieldMappingCSVOutputConfig,
)
from tests.gim_config_helpers import build_field_schema, build_gim_config


def test_field_mapping_csv_output_happy_path(tmp_path: Path) -> None:
    """Emits one CSV row per (event type, field) pair with joined field_schema metadata."""
    plugin = FieldMappingCSVOutput()

    gim_config = build_gim_config(
        category_required=["application_name", "user_name"],
        subcat_required=["event_outcome"],
        subcat_optional=["user_domain"],
        field_schema={
            **build_field_schema(
                "application", "name", description="Application name", example_values="sshd"
            ),
            "user": {
                "fields": [
                    {
                        "field_suffix": "name",
                        "field_type": "keyword",
                        "description": "User name",
                        "example_values": "admin",
                    },
                    {
                        "field_suffix": "domain",
                        "field_type": "keyword",
                        "description": "User domain",
                        "example_values": "CORP",
                    },
                ],
            },
            **build_field_schema("event", "outcome", description="Event outcome", example_values="success"),
        },
    )

    plugin_config = FieldMappingCSVOutputConfig(output_filename="test_output.csv")

    plugin.generate(gim_config, tmp_path, plugin_config)

    output_file = tmp_path / "test_output.csv"
    assert output_file.exists()

    with output_file.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert [row["Field Name"] for row in rows] == [
        "application_name",
        "event_outcome",
        "user_name",
        "user_domain",
    ]
    assert [row["Field Status"] for row in rows] == [
        "required",
        "required",
        "required",
        "optional",
    ]
    for row in rows:
        assert row["gim_event_type_code"] == "100000"
        assert row["gim_event_class"] == ""
        assert row["gim_event_category"] == "authentication"
        assert row["gim_event_subcategory"] == "authentication.logon"
        assert row["gim_event_type"] == "logon"

    user_name_row = rows[2]
    assert user_name_row["Field Description"] == "User name"
    assert user_name_row["Field Data Type"] == "keyword"
    assert user_name_row["Field Example"] == "admin"
