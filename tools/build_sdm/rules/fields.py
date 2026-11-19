"""Rules on field references: every listed field exists, and wildcards are sub-field groups only."""

from collections.abc import Iterator
from typing import Any

from build_sdm.rules.model import FIELD_LISTS, SdmModel, Violation, gim_key, iter_subcategories

__all__ = ["check_fields_exist", "check_wildcards", "known_fields", "sub_field_groups"]


def known_fields(field_schema: dict[str, Any]) -> set[str]:
    """Return every full field name the schema defines.

    Top entities prefix their suffixes with the entity name, sub entities compose
    "<parent>_<sub>_<suffix>" for each parent in applies_to, and reserved entities
    use the suffix as the literal field name.

    Args:
        field_schema: Field schema entities keyed by entity name.

    Returns:
        The set of full field names.
    """
    names: set[str] = set()
    for entity, data in field_schema.items():
        suffixes = [f.get("field_suffix") for f in data.get("fields", [])]
        match data.get("entity_type"):
            case "top":
                names.update(f"{entity}_{s}" for s in suffixes)
            case "reserved":
                names.update(str(s) for s in suffixes)
            case "sub":
                for parent in data.get("applies_to") or []:
                    names.update(f"{parent}_{entity}_{s}" for s in suffixes)
    return names


def sub_field_groups(field_schema: dict[str, Any]) -> set[str]:
    """Return every valid sub-field group wildcard, "<parent>_<sub>_*"."""
    return {
        f"{parent}_{entity}_*"
        for entity, data in field_schema.items()
        if data.get("entity_type") == "sub"
        for parent in data.get("applies_to") or []
    }


def _field_lists(model: SdmModel) -> Iterator[tuple[str, str, list[str], str]]:
    """Yield (entry_key prefix, list name, fields, file) for every category and subcategory field list."""
    for name, category in sorted(model.gim.items()):
        for list_name in FIELD_LISTS:
            fields = category.get(list_name) or []
            yield gim_key(category["code"]), list_name, fields, model.category_file(name)
    for sub in iter_subcategories(model):
        for list_name in FIELD_LISTS:
            fields = sub.data.get(list_name) or []
            yield sub.key, list_name, fields, model.category_file(sub.category_name)


def check_fields_exist(model: SdmModel) -> Iterator[Violation]:
    """Every non-wildcard entry in a required/recommended/optional list is a schema field."""
    known = known_fields(model.field_schema)
    for prefix, list_name, fields, file in _field_lists(model):
        for field in fields:
            if "*" not in field and field not in known:
                message = f'{list_name} lists "{field}", which no field schema entity defines'
                yield Violation("fields-exist", f"{prefix}/{list_name}/{field}", message, file)


def check_wildcards(model: SdmModel) -> Iterator[Violation]:
    """No wildcard in required_fields; elsewhere only "<parent>_<sub>_*" sub-field groups."""
    groups = sub_field_groups(model.field_schema)
    for prefix, list_name, fields, file in _field_lists(model):
        for field in fields:
            if "*" not in field:
                continue
            if list_name == "required_fields":
                message = f'required_fields must list fields explicitly, not the wildcard "{field}"'
            elif field not in groups:
                message = (
                    f'{list_name} wildcard "{field}" is not a sub-field group; '
                    "list the fields, or use <parent>_<sub>_* for a sub entity in that parent's applies_to"
                )
            else:
                continue
            yield Violation("wildcards", f"{prefix}/{list_name}/{field}", message, file)
