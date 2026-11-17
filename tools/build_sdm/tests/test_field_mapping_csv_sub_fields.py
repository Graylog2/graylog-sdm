"""Tests for FieldMappingCSVOutput's resolution of composed and wildcard sub-fields."""

import csv
from pathlib import Path

import pytest

from output_plugins.field_mapping_csv_output import (
    FieldMappingCSVOutput,
    FieldMappingCSVOutputConfig,
)
from tests.gim_config_helpers import build_field_schema, build_gim_config


def _hash_sub_field_schema() -> dict[str, object]:
    """A field_schema fragment: file/process "top" entities plus a hash "sub" entity."""
    return {
        **build_field_schema("file", "name", description="File name", example_values="a.exe"),
        **build_field_schema("process", "name", description="Process name", example_values="svchost.exe"),
        "hash": {
            "entity_type": "sub",
            "applies_to": ["file", "process"],
            "fields": [
                {
                    "field_suffix": "sha256",
                    "field_type": "keyword",
                    "description": "SHA256 hash value.",
                    "example_values": "",
                },
                {
                    "field_suffix": "md5",
                    "field_type": "keyword",
                    "description": "MD5 hash value.",
                    "example_values": "",
                },
            ],
        },
    }


def test_composed_sub_field_name_resolves_without_unchecked_fields(tmp_path: Path) -> None:
    """A composed name like file_hash_sha256 resolves via field_schema_map directly."""
    plugin = FieldMappingCSVOutput()

    gim_config = build_gim_config(
        category_optional=["file_hash_sha256"],
        field_schema=_hash_sub_field_schema(),
    )

    plugin_config = FieldMappingCSVOutputConfig(output_filename="test_output.csv")
    plugin.generate(gim_config, tmp_path, plugin_config)

    with (tmp_path / "test_output.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert [row["Field Name"] for row in rows] == ["file_hash_sha256"]
    assert rows[0]["Field Description"] == "SHA256 hash value."


def test_bare_sub_entity_field_name_does_not_resolve(tmp_path: Path) -> None:
    """A bare sub-entity field name (no parent prefix) has no field_schema match."""
    plugin = FieldMappingCSVOutput()

    gim_config = build_gim_config(
        category_optional=["hash_sha256"],
        field_schema=_hash_sub_field_schema(),
    )

    plugin_config = FieldMappingCSVOutputConfig(output_filename="test_output.csv")

    with pytest.raises(ValueError, match="no matching field_schema entry"):
        plugin.generate(gim_config, tmp_path, plugin_config)


def test_wildcard_optional_field_expands_to_all_matches(tmp_path: Path) -> None:
    """A wildcard like file_hash_* expands to every matching composed field name."""
    plugin = FieldMappingCSVOutput()

    gim_config = build_gim_config(
        category_optional=["file_hash_*"],
        field_schema=_hash_sub_field_schema(),
    )

    plugin_config = FieldMappingCSVOutputConfig(output_filename="test_output.csv")
    plugin.generate(gim_config, tmp_path, plugin_config)

    with (tmp_path / "test_output.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert sorted(row["Field Name"] for row in rows) == ["file_hash_md5", "file_hash_sha256"]
    assert {row["Field Status"] for row in rows} == {"optional"}


def test_wildcard_with_no_matches_raises(tmp_path: Path) -> None:
    """A wildcard that matches no field_schema entries raises ValueError."""
    plugin = FieldMappingCSVOutput()

    gim_config = build_gim_config(
        category_optional=["file_does_not_exist_*"],
        field_schema=_hash_sub_field_schema(),
    )

    plugin_config = FieldMappingCSVOutputConfig(output_filename="test_output.csv")

    with pytest.raises(ValueError, match="matched no field_schema entries"):
        plugin.generate(gim_config, tmp_path, plugin_config)


def test_wildcard_in_required_fields_raises(tmp_path: Path) -> None:
    """A wildcard used in required_fields is rejected, even though it would match."""
    plugin = FieldMappingCSVOutput()

    gim_config = build_gim_config(
        category_required=["file_hash_*"],
        field_schema=_hash_sub_field_schema(),
    )

    plugin_config = FieldMappingCSVOutputConfig(output_filename="test_output.csv")

    with pytest.raises(ValueError, match='only allowed for "recommended" or "optional"'):
        plugin.generate(gim_config, tmp_path, plugin_config)
