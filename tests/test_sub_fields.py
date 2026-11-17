"""Tests for gim_schema.sub_fields: applies_to validation and sub-field expansion."""

from typing import Any

import pytest

from build_sdm.gim_schema.sub_fields import expand_sub_fields, validate_applies_to


def _field(suffix: str, field_type: str = "keyword") -> dict[str, str]:
    """Build a minimal field_schema field entry for test fixtures."""
    return {
        "field_suffix": suffix,
        "field_type": field_type,
        "description": f"{suffix} description",
        "example_values": "",
    }


def test_validate_applies_to_accepts_known_top_entities() -> None:
    """A sub-entity's applies_to referencing real top entities passes validation."""
    field_schema: dict[str, Any] = {
        "file": {"entity_type": "top", "fields": []},
        "process": {"entity_type": "top", "fields": []},
        "hash": {
            "entity_type": "sub",
            "applies_to": ["file", "process"],
            "fields": [_field("md5")],
        },
    }

    validate_applies_to(field_schema)


def test_validate_applies_to_rejects_unknown_parent() -> None:
    """A sub-entity's applies_to referencing a non-existent entity raises ValueError."""
    field_schema: dict[str, Any] = {
        "hash": {
            "entity_type": "sub",
            "applies_to": ["does_not_exist"],
            "fields": [_field("md5")],
        },
    }

    with pytest.raises(ValueError, match="does_not_exist"):
        validate_applies_to(field_schema)


def test_validate_applies_to_rejects_non_top_parent() -> None:
    """A sub-entity's applies_to referencing a sub or reserved entity raises ValueError."""
    field_schema: dict[str, Any] = {
        "geo": {"entity_type": "sub", "applies_to": ["source"], "fields": []},
        "hash": {
            "entity_type": "sub",
            "applies_to": ["geo"],
            "fields": [_field("md5")],
        },
    }

    with pytest.raises(ValueError, match="geo"):
        validate_applies_to(field_schema)


def test_expand_sub_fields_composes_field_names_per_parent() -> None:
    """expand_sub_fields composes {parent}_{sub_entity}_{suffix} field names."""
    field_schema: dict[str, Any] = {
        "file": {"entity_type": "top", "fields": []},
        "process": {"entity_type": "top", "fields": []},
        "hash": {
            "entity_type": "sub",
            "applies_to": ["file", "process"],
            "fields": [_field("md5"), _field("sha256")],
        },
    }

    expanded = expand_sub_fields(field_schema)

    file_field_names = {row["field"] for row in expanded["file"]}
    process_field_names = {row["field"] for row in expanded["process"]}
    assert file_field_names == {"file_hash_md5", "file_hash_sha256"}
    assert process_field_names == {"process_hash_md5", "process_hash_sha256"}
    assert all(row["source_entity"] == "hash" for row in expanded["file"])


def test_expand_sub_fields_omits_parents_with_no_sub_fields() -> None:
    """A top entity with no attached sub-entities is absent from the expansion."""
    field_schema: dict[str, Any] = {
        "user": {"entity_type": "top", "fields": []},
    }

    assert expand_sub_fields(field_schema) == {}


def test_expand_sub_fields_merges_multiple_sub_entities_on_one_parent() -> None:
    """Multiple sub-entities attached to the same parent both contribute rows."""
    field_schema: dict[str, Any] = {
        "source": {"entity_type": "top", "fields": []},
        "geo": {
            "entity_type": "sub",
            "applies_to": ["source"],
            "fields": [_field("city")],
        },
        "as": {
            "entity_type": "sub",
            "applies_to": ["source"],
            "fields": [_field("number")],
        },
    }

    expanded = expand_sub_fields(field_schema)

    field_names = {row["field"] for row in expanded["source"]}
    assert field_names == {"source_geo_city", "source_as_number"}
