"""Tests for validate_field_types: field types are checked against the configured allowlist."""

from pathlib import Path
from typing import Any

import pytest

from build_sdm.gim_schema.field_types import validate_field_types
from build_sdm.runner import _load_and_transform_gim_config


def _gim_config(allowed: list[str] | None, field_types: dict[str, str]) -> dict[str, Any]:
    """Build a restructured gim_config with one 'alert' entity.

    Args:
        allowed: The allowed_field_types list, or None to omit it.
        field_types: field_suffix -> field_type for the entity's fields.

    Returns:
        A minimal restructured gim_config.
    """
    config: dict[str, Any] = {"field_schema_config": {}}
    if allowed is not None:
        config["field_schema_config"]["allowed_field_types"] = allowed
    fields = [{"field_suffix": s, "field_type": t} for s, t in field_types.items()]
    return {"config": config, "field_schema": {"alert": {"entity_type": "top", "fields": fields}}}


def test_allowed_types_pass() -> None:
    """Fields whose types are all in the allowlist pass."""
    validate_field_types(_gim_config(["keyword", "long"], {"id": "keyword", "count": "long"}))


def test_disallowed_types_are_all_listed() -> None:
    """Every field with a type outside the allowlist is reported, not just the first."""
    gim_config = _gim_config(["keyword"], {"id": "keyword", "count": "long", "ok": "float"})

    with pytest.raises(ValueError, match=r"Invalid field_type in 2 field\(s\)") as excinfo:
        validate_field_types(gim_config)

    assert 'alert.count: "long"' in str(excinfo.value)
    assert 'alert.ok: "float"' in str(excinfo.value)


def test_missing_allowlist_raises() -> None:
    """Field definitions without an allowlist to check them against are an error."""
    with pytest.raises(ValueError, match="allowed_field_types is missing"):
        validate_field_types(_gim_config(None, {"id": "keyword"}))


def test_no_field_schema_needs_no_allowlist() -> None:
    """A config with no field_schema entities has nothing to check."""
    validate_field_types({"config": {}})


def test_real_data_types_are_all_allowed(repo_root: Path) -> None:
    """The real SDM source loads: every field_type it uses is in its configured allowlist."""
    result = _load_and_transform_gim_config(repo_root, {"global": {"sdm_source_dir": "src/sdm"}})

    used = {f["field_type"] for e in result["field_schema"].values() for f in e.get("fields", [])}
    allowed = set(result["config"]["field_schema_config"]["allowed_field_types"])
    assert {"long", "boolean", "byte"} <= used
    assert used <= allowed


def test_load_rejects_type_not_in_config(tmp_path: Path) -> None:
    """End to end: a source tree whose allowlist omits a used type fails to load."""
    source = tmp_path / "src" / "sdm"
    source.mkdir(parents=True)
    (source / "field_schema.config.toml").write_text(
        'type = "config"\n\n[field_schema_config]\nallowed_field_types = ["keyword"]\n',
        encoding="utf-8",
    )
    (source / "alert.toml").write_text(
        'type = "field_schema"\n\n[alert]\ndescription = "Alert"\nentity_type = "top"\n\n'
        '[[alert.fields]]\nfield_suffix = "count"\nfield_type = "long"\ndescription = "Count"\n',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match='alert.count: "long"'):
        _load_and_transform_gim_config(tmp_path, {"global": {"sdm_source_dir": "src/sdm"}})


PREVIOUSLY_ACCEPTED_TYPES = {
    "text", "keyword", "keyword/lowercase", "integer", "long", "short",
    "byte", "double", "float", "half_float", "scaled_float", "date",
    "boolean", "binary", "integer_range", "float_range", "long_range",
    "double_range", "date_range", "ip", "object", "nested", "alias",
}  # fmt: skip


def test_allowlist_keeps_every_previously_accepted_type(repo_root: Path) -> None:
    """The configured allowlist is the set the tool hard-coded, so nothing that built before is rejected.

    Narrowing it is a deliberate SDM change policy decision (follow-up F17); update this test then.
    """
    result = _load_and_transform_gim_config(repo_root, {"global": {"sdm_source_dir": "src/sdm"}})

    assert set(result["config"]["field_schema_config"]["allowed_field_types"]) == PREVIOUSLY_ACCEPTED_TYPES


@pytest.mark.parametrize(
    "allowed",
    ["keyword", ["keyword", 1], ["keyword", ["long"]], {"keyword": True}],
    ids=["string", "non-string-item", "nested-list", "table"],
)
def test_malformed_allowlist_raises(allowed: Any) -> None:
    """An allowlist that isn't a list of strings is rejected, not silently reinterpreted."""
    gim_config = _gim_config(["keyword"], {"id": "keyword"})
    gim_config["config"]["field_schema_config"]["allowed_field_types"] = allowed

    with pytest.raises(ValueError, match="must be a list of strings"):
        validate_field_types(gim_config)
