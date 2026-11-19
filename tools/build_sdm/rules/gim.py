"""Rules on GIM structure: naming, uniqueness, the default subcategory and codes."""

import re
from collections import defaultdict
from collections.abc import Iterator

from build_sdm.rules.model import SdmModel, Subcategory, Violation, gim_key, iter_subcategories

__all__ = ["check_codes", "check_default_99", "check_default_baseline", "check_naming", "check_unique_names"]

NAME_PATTERN = re.compile(r"^[a-z]+(_[a-z]+)*$")
DEFAULT_NAME = "default"
DEFAULT_CODE = "99"
FILE_PREFIX = re.compile(r"^(\d+)\.")


def _bad_name(kind: str, name: object) -> str | None:
    """Return a message if name breaks the naming convention, else None."""
    if isinstance(name, str) and NAME_PATTERN.fullmatch(name):
        return None
    return f'{kind} name "{name}" must be lowercase a-z words separated by underscores'


def check_naming(model: SdmModel) -> Iterator[Violation]:
    """Class, category, subcategory and event type names are lowercase a-z words joined by underscores."""
    for name, category in sorted(model.gim.items()):
        file = model.category_file(name)
        if message := _bad_name("category", category.get("name")):
            yield Violation("naming", gim_key(category["code"], attr="name"), message, file)

    for sub in iter_subcategories(model):
        file = model.category_file(sub.category_name)
        if message := _bad_name("subcategory", sub.data.get("name")):
            yield Violation("naming", f"{sub.key}/name", message, file)
        if "class" in sub.data and (message := _bad_name("class", sub.data["class"])):
            yield Violation("naming", f"{sub.key}/class", message, file)
        for code, event_type in sorted(sub.data.get("event_type_codes", {}).items()):
            if message := _bad_name("event type", event_type.get("name")):
                key = gim_key(sub.category["code"], sub.code, code, attr="name")
                yield Violation("naming", key, message, file)


def check_unique_names(model: SdmModel) -> Iterator[Violation]:
    """Subcategory and event type names are unique across the GIM, except "default"."""
    subcategories: dict[str, list[tuple[str, str]]] = defaultdict(list)
    event_types: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for sub in iter_subcategories(model):
        file = model.category_file(sub.category_name)
        subcategories[sub.data.get("name", "")].append((f"{sub.key}/name", file))
        for code, event_type in sorted(sub.data.get("event_type_codes", {}).items()):
            key = gim_key(sub.category["code"], sub.code, code, attr="name")
            event_types[event_type.get("name", "")].append((key, file))

    for kind, names in (("subcategory", subcategories), ("event type", event_types)):
        for name, uses in sorted(names.items()):
            if name == DEFAULT_NAME or len(uses) < 2:
                continue
            for key, file in uses:
                others = ", ".join(k.split("/")[0] for k, _ in uses if k != key)
                yield Violation("unique-names", key, f'{kind} name "{name}" is also used by {others}', file)


def check_default_99(model: SdmModel) -> Iterator[Violation]:
    """A subcategory named "default" has code 99, and code 99 is named "default"."""
    for sub in iter_subcategories(model):
        file = model.category_file(sub.category_name)
        name = sub.data.get("name")
        if name == DEFAULT_NAME and sub.code != DEFAULT_CODE:
            message = f'the "default" subcategory must have code {DEFAULT_CODE}, not {sub.code}'
            yield Violation("default-99", f"{sub.key}/code", message, file)
        elif sub.code == DEFAULT_CODE and name != DEFAULT_NAME:
            message = f'subcategory code {DEFAULT_CODE} is reserved for "default", not "{name}"'
            yield Violation("default-99", f"{sub.key}/name", message, file)


def check_default_baseline(model: SdmModel) -> Iterator[Violation]:
    """Every subcategory requires at least the fields its category's default subcategory requires."""
    defaults: dict[str, Subcategory] = {}
    for sub in iter_subcategories(model):
        if sub.data.get("name") == DEFAULT_NAME:
            defaults.setdefault(sub.category_name, sub)

    for sub in iter_subcategories(model):
        default = defaults.get(sub.category_name)
        if default is None or sub.data.get("name") == DEFAULT_NAME:
            continue
        covered = set(sub.data.get("required_fields") or []) | set(sub.category.get("required_fields") or [])
        for field in sorted(set(default.data.get("required_fields") or []) - covered):
            message = f'required_fields must include "{field}", required by the default subcategory'
            message += f" {default.key}"
            key = f"{sub.key}/required_fields/{field}"
            yield Violation("default-baseline", key, message, model.category_file(sub.category_name))


def check_codes(model: SdmModel) -> Iterator[Violation]:
    """Category codes are unique, and each file's NN. prefix equals its category code."""
    by_code: dict[str, list[str]] = defaultdict(list)
    for name, category in sorted(model.gim.items()):
        by_code[category["code"]].append(name)

    for name, category in sorted(model.gim.items()):
        code = category["code"]
        file = model.category_file(name)
        others = [n for n in by_code[code] if n != name]
        if others:
            message = f"category code {code} is also used by {', '.join(others)}"
            yield Violation("codes", gim_key(code, attr="code"), message, file)

        file_name = file.rsplit("/", 1)[-1]
        prefix = FILE_PREFIX.match(file_name)
        if prefix is None or prefix.group(1) != code:
            message = f'file name "{file_name}" must start with the category code "{code}."'
            yield Violation("codes", gim_key(code, attr="file"), message, file)
