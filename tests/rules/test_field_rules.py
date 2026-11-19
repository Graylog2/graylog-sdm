"""Tests for the fields-exist and wildcards rules."""

from typing import Any

from build_sdm.rules import RULES
from build_sdm.rules.fields import known_fields
from tests.gim_config_helpers import build_field_schema
from tests.rules.helpers import build_gim_config, model_from


def _schema() -> dict[str, Any]:
    """Return a schema with a top entity, a sub entity applied to it, and a reserved entity."""
    schema = build_field_schema("file", "name", entity_type="top")
    schema |= build_field_schema("hash", "sha256", entity_type="sub", applies_to=["file"])
    schema |= build_field_schema("reserved", "event_source", entity_type="reserved")
    return schema


def _keys(rule_id: str, **lists: list[str]) -> list[str]:
    """Run a rule against a subcategory with the given field lists; return the entry_keys."""
    gim_config = build_gim_config(field_schema=_schema(), **lists)  # type: ignore[arg-type]
    return [v.entry_key for v in RULES[rule_id](model_from(gim_config))]


def test_known_fields_composes_top_sub_and_reserved_names() -> None:
    """Field names follow the entity_type composition rules."""
    assert known_fields(_schema()) == {"file_name", "file_hash_sha256", "event_source"}


def test_existing_fields_pass() -> None:
    """Top, composed sub and reserved field names all resolve."""
    lists = {
        "subcat_required": ["file_name"],
        "subcat_recommended": ["file_hash_sha256"],
        "category_optional": ["event_source"],
    }

    assert _keys("fields-exist", **lists) == []


def test_unknown_field_is_reported_per_list() -> None:
    """A field no entity defines is reported under the list and level that names it."""
    keys = _keys("fields-exist", subcat_required=["file_size"], category_optional=["hash_sha256"])

    assert keys == ["gim:10/optional_fields/hash_sha256", "gim:10.00/required_fields/file_size"]


def test_fields_exist_ignores_wildcards() -> None:
    """Wildcards are left to the wildcards rule, so nothing is reported twice."""
    assert _keys("fields-exist", subcat_optional=["file_*"]) == []


def test_sub_field_group_wildcard_passes_outside_required() -> None:
    """A <parent>_<sub>_* group for a real sub entity is allowed in recommended and optional."""
    assert _keys("wildcards", subcat_recommended=["file_hash_*"], subcat_optional=["file_hash_*"]) == []


def test_wildcard_in_required_is_reported() -> None:
    """No wildcard is allowed in required, even a valid sub-field group."""
    assert _keys("wildcards", subcat_required=["file_hash_*"]) == ["gim:10.00/required_fields/file_hash_*"]


def test_broad_or_unknown_wildcards_are_reported() -> None:
    """Entity-wide wildcards and groups for a sub entity not applied to that parent are reported."""
    keys = _keys("wildcards", subcat_optional=["file_*", "process_hash_*", "file_*_sha256"])

    assert keys == [
        "gim:10.00/optional_fields/file_*",
        "gim:10.00/optional_fields/process_hash_*",
        "gim:10.00/optional_fields/file_*_sha256",
    ]
