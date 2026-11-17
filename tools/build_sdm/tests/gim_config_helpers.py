"""Shared gim_config builders for FieldMappingCSVOutput tests."""

from typing import Any


def build_gim_config(
    *,
    category_code: str = "10",
    category_name: str = "authentication",
    category_required: list[str] | None = None,
    category_recommended: list[str] | None = None,
    category_optional: list[str] | None = None,
    subcat_code: str = "00",
    subcat_name: str = "logon",
    subcat_required: list[str] | None = None,
    subcat_recommended: list[str] | None = None,
    subcat_optional: list[str] | None = None,
    event_type_codes: dict[str, str] | None = None,
    field_schema: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a minimal one-category/one-subcategory gim_config for plugin tests.

    Args:
        category_code: The category's 2-digit GIM code.
        category_name: The category's key and display name in gim_config["gim"].
        category_required: Category-level required_fields.
        category_recommended: Category-level recommended_fields.
        category_optional: Category-level optional_fields.
        subcat_code: The subcategory's 2-digit GIM code.
        subcat_name: The subcategory's name.
        subcat_required: Subcategory-level required_fields.
        subcat_recommended: Subcategory-level recommended_fields.
        subcat_optional: Subcategory-level optional_fields.
        event_type_codes: Mapping of event type code to name; defaults to a
            single entry keyed by subcat_code, named subcat_name.
        field_schema: The gim_config["field_schema"] section; defaults to empty.

    Returns:
        A gim_config dict with "gim" and "field_schema" top-level keys.
    """
    if event_type_codes is None:
        event_type_codes = {subcat_code: subcat_name}

    return {
        "gim": {
            category_name: {
                "code": category_code,
                "name": category_name,
                "required_fields": category_required or [],
                "recommended_fields": category_recommended or [],
                "optional_fields": category_optional or [],
                "subcategories": {
                    subcat_code: {
                        "name": subcat_name,
                        "required_fields": subcat_required or [],
                        "recommended_fields": subcat_recommended or [],
                        "optional_fields": subcat_optional or [],
                        "event_type_codes": {code: {"name": name} for code, name in event_type_codes.items()},
                    },
                },
            },
        },
        "field_schema": field_schema or {},
    }


def build_field_schema(
    entity_name: str,
    field_suffix: str,
    *,
    field_type: str = "keyword",
    description: str = "Test field.",
    example_values: str = "example",
    entity_type: str | None = None,
    applies_to: list[str] | None = None,
) -> dict[str, Any]:
    """Build a single-entity, single-field field_schema dict.

    Args:
        entity_name: The field_schema entity name (e.g. "user").
        field_suffix: The field's suffix (e.g. "domain").
        field_type: The field's declared type.
        description: The field's description.
        example_values: The field's example values.
        entity_type: Optional field_schema entity_type ("top"/"sub"/"reserved").
            An omitted entity_type behaves like "top" in _build_field_schema_map.
        applies_to: Optional list of parent entity names this sub-entity's
            fields compose onto; only meaningful when entity_type="sub".

    Returns:
        A field_schema dict with one entity containing one field; the entity
        also includes entity_type and/or applies_to when those are passed.
    """
    entity: dict[str, Any] = {
        "fields": [
            {
                "field_suffix": field_suffix,
                "field_type": field_type,
                "description": description,
                "example_values": example_values,
            },
        ],
    }
    if entity_type is not None:
        entity["entity_type"] = entity_type
    if applies_to is not None:
        entity["applies_to"] = applies_to

    return {entity_name: entity}
