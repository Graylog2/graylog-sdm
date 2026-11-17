"""Compose and validate sub-field entity relationships within field_schema data."""

from typing import Any, TypedDict


class SubFieldRow(TypedDict):
    """A field composed by appending a sub-entity's fields onto a parent entity."""

    field: str
    field_type: str
    description: str
    example_values: str
    source_entity: str


def validate_applies_to(field_schema: dict[str, Any]) -> None:
    """Validate that every sub-entity's applies_to list names a real top entity.

    Args:
        field_schema: Flattened field_schema entities keyed by entity name, as
            produced by config_loader's field_schema loading/merge.

    Raises:
        ValueError: If a sub-entity's applies_to references a name that isn't a
            loaded entity with entity_type == "top".
    """
    top_entities = {
        name
        for name, entity_data in field_schema.items()
        if isinstance(entity_data, dict) and entity_data.get("entity_type") == "top"
    }

    for name, entity_data in field_schema.items():
        if not isinstance(entity_data, dict) or entity_data.get("entity_type") != "sub":
            continue

        for parent in entity_data.get("applies_to") or []:
            if parent not in top_entities:
                raise ValueError(
                    f'Sub-field entity "{name}" declares applies_to "{parent}", '
                    'which is not a known field_schema entity with entity_type "top".'
                )


def expand_sub_fields(field_schema: dict[str, Any]) -> dict[str, list[SubFieldRow]]:
    """Compose sub-entity fields onto every parent entity that declares them.

    Args:
        field_schema: Flattened field_schema entities keyed by entity name.

    Returns:
        Mapping of parent entity name to the list of composed field rows
        (field name f"{parent}_{sub_entity_name}_{field_suffix}") attached to it.
    """
    expanded: dict[str, list[SubFieldRow]] = {}

    for sub_entity_name, entity_data in field_schema.items():
        if not isinstance(entity_data, dict) or entity_data.get("entity_type") != "sub":
            continue

        for parent in entity_data.get("applies_to") or []:
            rows = expanded.setdefault(parent, [])
            for field in entity_data.get("fields", []):
                rows.append(
                    SubFieldRow(
                        field=f"{parent}_{sub_entity_name}_{field['field_suffix']}",
                        field_type=field["field_type"],
                        description=field["description"],
                        example_values=field.get("example_values") or "",
                        source_entity=sub_entity_name,
                    )
                )

    return expanded
