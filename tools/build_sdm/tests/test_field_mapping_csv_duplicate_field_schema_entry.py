"""Duplicate field_schema entry error test for FieldMappingCSVOutput."""

from pathlib import Path

import pytest

from output_plugins.field_mapping_csv_output import FieldMappingCSVOutput
from tests.gim_config_helpers import build_gim_config


def test_duplicate_field_suffix_in_one_entity_raises(tmp_path: Path) -> None:
    """A field_schema entity listing the same field_suffix twice halts the build.

    Silently keeping the last entry would corrupt the CSV with the wrong
    description/type/example for that field.
    """
    plugin = FieldMappingCSVOutput()

    gim_config = build_gim_config(
        category_required=["user_domain"],
        field_schema={
            "user": {
                "fields": [
                    {
                        "field_suffix": "domain",
                        "field_type": "keyword",
                        "description": "First definition",
                        "example_values": "CORP",
                    },
                    {
                        "field_suffix": "domain",
                        "field_type": "keyword",
                        "description": "Second definition",
                        "example_values": "EXAMPLE",
                    },
                ],
            },
        },
    )

    with pytest.raises(ValueError, match="more than once"):
        plugin.generate(gim_config, tmp_path)
