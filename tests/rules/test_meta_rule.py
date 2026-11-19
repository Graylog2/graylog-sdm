"""Tests for the ascii-meta rule."""

from typing import Any

from build_sdm.rules import RULES
from tests.gim_config_helpers import build_field_schema
from tests.rules.helpers import build_gim_config, model_from


def _keys(gim_config: dict[str, Any]) -> list[str]:
    """Return the entry_keys of ascii-meta violations."""
    return [v.entry_key for v in RULES["ascii-meta"](model_from(gim_config))]


def test_ascii_text_with_newlines_and_tabs_passes() -> None:
    """Printable ASCII, newlines and tabs are allowed."""
    gim_config = build_gim_config(field_schema=build_field_schema("user", "name", entity_type="top"))
    gim_config["gim"]["authentication"]["description"] = "Line one.\n\tLine two (indented): `code` ~ ok."

    assert _keys(gim_config) == []


def test_non_ascii_is_reported_with_character_names() -> None:
    """Each offending text is reported once, naming the characters it contains."""
    gim_config = build_gim_config()
    gim_config["gim"]["authentication"]["description"] = "It’s an — example—"

    violations = list(RULES["ascii-meta"](model_from(gim_config)))

    assert [v.entry_key for v in violations] == ["gim:10/description"]
    assert "U+2014 EM DASH" in violations[0].message
    assert "U+2019 RIGHT SINGLE QUOTATION MARK" in violations[0].message


def test_control_characters_are_reported() -> None:
    """Non-printable ASCII such as a carriage return is not allowed."""
    gim_config = build_gim_config()
    gim_config["gim"]["authentication"]["description"] = "Windows line\r\n"

    assert _keys(gim_config) == ["gim:10/description"]


def test_every_meta_location_is_checked() -> None:
    """Category, template, subcategory, summary, event type and schema text are all checked."""
    bad = "café"
    gim_config = build_gim_config(
        field_schema=build_field_schema("user", "name", entity_type="top", description=bad)
    )
    category = gim_config["gim"]["authentication"]
    category["summaries"] = [{"template_id": "basic", "title": bad, "description": "ok"}]
    category["indicators"] = [{"type": "outcome", "title": "ok", "description": bad}]
    subcategory = category["subcategories"]["00"]
    subcategory["description"] = bad
    subcategory["summary"] = {"title": bad}
    subcategory["event_type_codes"]["00"]["description"] = bad
    gim_config["field_schema"]["user"].update(title=bad, description=bad)

    assert sorted(_keys(gim_config)) == [
        "gim:10.00.00/description",
        "gim:10.00/description",
        "gim:10.00/summary/title",
        "gim:10/indicators/outcome/description",
        "gim:10/summaries/basic/title",
        "schema:user/description",
        "schema:user/fields/name/description",
        "schema:user/title",
    ]
