"""Validate schema field types against the configured allowlist."""

from typing import Any

__all__ = ["validate_field_types"]


def validate_field_types(gim_config: dict[str, Any]) -> None:
    """Check every field_schema field's field_type against config.field_schema_config.allowed_field_types.

    The allowlist lives in the SDM source (src/sdm/config/field_schema.config.toml), so it is
    checked after all files are loaded rather than inside the field model, which can't see it.

    Args:
        gim_config: The restructured gim_config ('config' and 'field_schema' sections).

    Raises:
        ValueError: If there are field_schema entities but no allowed_field_types list, or if
            any field uses a type that isn't in the list. All invalid fields are listed.
    """
    field_schema: dict[str, Any] = gim_config.get("field_schema", {})
    if not field_schema:
        return

    field_schema_config = gim_config.get("config", {}).get("field_schema_config", {})
    allowed = field_schema_config.get("allowed_field_types")
    if not allowed:
        raise ValueError(
            "config.field_schema_config.allowed_field_types is missing or empty; "
            "it is required to validate field_schema field types."
        )
    allowed_set = set(allowed)

    invalid = [
        f'{entity_name}.{field.get("field_suffix")}: "{field.get("field_type")}"'
        for entity_name, entity in sorted(field_schema.items())
        for field in entity.get("fields", [])
        if field.get("field_type") not in allowed_set
    ]
    if invalid:
        raise ValueError(
            f"Invalid field_type in {len(invalid)} field(s); allowed types are "
            f"{sorted(allowed_set)}:\n  " + "\n  ".join(invalid)
        )
