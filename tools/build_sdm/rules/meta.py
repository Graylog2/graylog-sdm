"""The ascii-meta rule: descriptive text uses printable US-ASCII only."""

import unicodedata
from collections.abc import Iterator
from typing import Any

from build_sdm.rules.model import SdmModel, Violation, gim_key, iter_subcategories, schema_key

__all__ = ["check_ascii_meta"]

# Printable US-ASCII, plus the newline and tab that multiline strings contain.
ALLOWED = frozenset(chr(c) for c in range(0x20, 0x7F)) | {"\n", "\t"}
MAX_LISTED = 5


def _ascii_problem(value: object) -> str | None:
    """Return a description of the disallowed characters in value, or None if there are none."""
    if not isinstance(value, str):
        return None
    bad = sorted({ch for ch in value if ch not in ALLOWED})
    if not bad:
        return None
    listed = ", ".join(f"U+{ord(ch):04X} {unicodedata.name(ch, 'UNNAMED')}" for ch in bad[:MAX_LISTED])
    more = f" and {len(bad) - MAX_LISTED} more" if len(bad) > MAX_LISTED else ""
    return f"contains characters outside printable US-ASCII: {listed}{more}"


def _texts(category: dict[str, Any], code: str) -> Iterator[tuple[str, object]]:
    """Yield (entry_key, text) for a category's own meta text and its summary/indicator templates."""
    yield gim_key(code, attr="description"), category.get("description")
    for template in category.get("summaries") or []:
        for attr in ("title", "description"):
            yield (
                gim_key(code, attr="summaries", item=f"{template.get('template_id')}/{attr}"),
                template.get(attr),
            )
    for template in category.get("indicators") or []:
        for attr in ("title", "description"):
            yield gim_key(code, attr="indicators", item=f"{template.get('type')}/{attr}"), template.get(attr)


def check_ascii_meta(model: SdmModel) -> Iterator[Violation]:
    """Meta text in GIM categories, subcategories, event types and schema entities is printable US-ASCII."""
    texts: list[tuple[str, object, str]] = []
    for name, category in sorted(model.gim.items()):
        file = model.category_file(name)
        texts.extend((key, text, file) for key, text in _texts(category, category["code"]))

    for sub in iter_subcategories(model):
        file = model.category_file(sub.category_name)
        texts.append((f"{sub.key}/description", sub.data.get("description"), file))
        for attr, text in sorted((sub.data.get("summary") or {}).items()):
            texts.append((f"{sub.key}/summary/{attr}", text, file))
        for code, event_type in sorted(sub.data.get("event_type_codes", {}).items()):
            key = gim_key(sub.category["code"], sub.code, code, attr="description")
            texts.append((key, event_type.get("description"), file))

    for entity, data in sorted(model.field_schema.items()):
        file = model.entity_file(entity)
        for attr in ("title", "description"):
            texts.append((schema_key(entity, attr), data.get(attr), file))
        for field in data.get("fields", []):
            key = schema_key(entity, "fields", str(field.get("field_suffix")), "description")
            texts.append((key, field.get("description"), file))

    for key, text, file in texts:
        if problem := _ascii_problem(text):
            yield Violation("ascii-meta", key, problem, file)
