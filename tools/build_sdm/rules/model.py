"""The data the lint rules check, and the violations they report."""

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "FIELD_LISTS",
    "SdmModel",
    "Subcategory",
    "Violation",
    "gim_key",
    "iter_subcategories",
    "schema_key",
]

FIELD_LISTS = ("required_fields", "recommended_fields", "optional_fields")
UNKNOWN_FILE = "<unknown>"


@dataclass(frozen=True, slots=True)
class Violation:
    """One rule violation.

    Attributes:
        rule_id: Stable rule identifier, e.g. "naming".
        entry_key: Stable logical path to the offending entry, independent of line numbers.
            GIM entries are keyed by code so a rename keeps the key, e.g. "gim:10.05/name".
        message: What is wrong, for a human.
        file: Repo-relative path of the source file, e.g. "src/sdm/infomodels/10.authentication.toml".
        line: 1-based line of the entry in file, if it could be located. For display only: it
            moves whenever lines above it change, so it never affects whether a violation is new.
    """

    rule_id: str
    entry_key: str
    message: str
    file: str
    line: int | None = None


@dataclass(frozen=True, slots=True)
class SdmModel:
    """Loaded SDM source: the restructured 'gim' and 'field_schema' sections plus file locations.

    Attributes:
        gim: GIM categories keyed by category name.
        field_schema: Field schema entities keyed by entity name.
        category_files: Category name -> repo-relative source file.
        entity_files: Entity name -> repo-relative source file.
    """

    gim: dict[str, Any]
    field_schema: dict[str, Any]
    category_files: dict[str, str] = field(default_factory=dict)
    entity_files: dict[str, str] = field(default_factory=dict)

    def category_file(self, category: str) -> str:
        """Return the source file for a category, or a placeholder if unknown."""
        return self.category_files.get(category, UNKNOWN_FILE)

    def entity_file(self, entity: str) -> str:
        """Return the source file for a field schema entity, or a placeholder if unknown."""
        return self.entity_files.get(entity, UNKNOWN_FILE)


@dataclass(frozen=True, slots=True)
class Subcategory:
    """A subcategory together with the category it belongs to."""

    category_name: str
    category: dict[str, Any]
    code: str
    data: dict[str, Any]

    @property
    def key(self) -> str:
        """Return the subcategory's entry_key prefix, e.g. "gim:10.05"."""
        return gim_key(self.category["code"], self.code)


def gim_key(*codes: str, attr: str | None = None, item: str | None = None) -> str:
    """Build a GIM entry_key from codes, an optional attribute and an optional list item.

    Args:
        codes: Category code, then optionally subcategory and event type codes.
        attr: Attribute name, e.g. "name" or "required_fields".
        item: List item within the attribute, e.g. a field name.

    Returns:
        The key, e.g. "gim:10.05/required_fields/user_name".
    """
    key = "gim:" + ".".join(codes)
    if attr is not None:
        key += f"/{attr}"
    if item is not None:
        key += f"/{item}"
    return key


def schema_key(entity: str, *parts: str) -> str:
    """Build a field schema entry_key, e.g. "schema:user/fields/name/description"."""
    return "/".join([f"schema:{entity}", *parts])


def iter_subcategories(model: SdmModel) -> Iterator[Subcategory]:
    """Yield every subcategory in category-code, then subcategory-code order."""
    for name, category in sorted(model.gim.items(), key=lambda item: (item[1]["code"], item[0])):
        for code, data in sorted(category.get("subcategories", {}).items()):
            yield Subcategory(name, category, code, data)
