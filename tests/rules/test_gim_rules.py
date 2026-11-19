"""Tests for the GIM structure rules: naming, unique-names, default-99, default-baseline, codes."""

import pytest

from build_sdm.rules import RULES, Violation
from tests.rules.helpers import FILE, add_subcategory, build_gim_config, model_from


def _run(rule_id: str, gim_config: dict[str, object]) -> list[Violation]:
    """Run one rule against a gim_config."""
    return list(RULES[rule_id](model_from(gim_config)))


def test_conforming_gim_passes_every_structure_rule() -> None:
    """A conforming category produces no violations from any GIM structure rule."""
    gim_config = add_subcategory(build_gim_config(), "99", "default")

    for rule_id in ("naming", "unique-names", "default-99", "default-baseline", "codes"):
        assert _run(rule_id, gim_config) == [], rule_id


@pytest.mark.parametrize("name", ["Bad-Name", "two words", "name2", "_lead", "trail_", "Upper"])
def test_naming_rejects_bad_subcategory_name(name: str) -> None:
    """Subcategory names must be lowercase a-z words joined by single underscores."""
    violations = _run("naming", build_gim_config(subcat_name=name, event_type_codes={"00": "logon"}))

    assert [(v.rule_id, v.entry_key, v.file) for v in violations] == [("naming", "gim:10.00/name", FILE)]


def test_naming_checks_category_class_and_event_type() -> None:
    """Category, class and event type names are all checked, each under its own key."""
    gim_config = build_gim_config(category_name="Auth", event_type_codes={"03": "log on"})
    gim_config["gim"]["Auth"]["subcategories"]["00"]["class"] = "End-Point"

    keys = [v.entry_key for v in _run("naming", gim_config)]

    assert keys == ["gim:10/name", "gim:10.00/class", "gim:10.00.03/name"]


def test_unique_names_reports_every_use_of_a_duplicate() -> None:
    """Each subcategory sharing a name is reported, pointing at the others."""
    gim_config = add_subcategory(build_gim_config(subcat_name="logon"), "05", "logon")

    violations = _run("unique-names", gim_config)

    assert [v.entry_key for v in violations] == ["gim:10.00/name", "gim:10.05/name"]
    assert "gim:10.05" in violations[0].message


def test_unique_names_checks_event_types_across_categories() -> None:
    """Event type names must be unique across the whole GIM, not just within a category."""
    gim_config = build_gim_config(event_type_codes={"01": "error"})
    other = build_gim_config(
        category_code="11", category_name="iam", subcat_name="user", event_type_codes={"02": "error"}
    )
    gim_config["gim"].update(other["gim"])

    keys = [v.entry_key for v in _run("unique-names", gim_config)]

    assert keys == ["gim:10.00.01/name", "gim:11.00.02/name"]


def test_unique_names_allows_repeated_default() -> None:
    """The name "default" may repeat across categories."""
    gim_config = add_subcategory(build_gim_config(), "99", "default")
    other = add_subcategory(
        build_gim_config(category_code="11", category_name="iam", subcat_name="user"), "99", "default"
    )
    gim_config["gim"].update(other["gim"])
    for category in gim_config["gim"].values():
        category["subcategories"]["99"]["event_type_codes"] = {"99": {"name": "default"}}

    assert _run("unique-names", gim_config) == []


def test_default_99_rejects_default_with_other_code() -> None:
    """A subcategory named default must have code 99."""
    violations = _run("default-99", add_subcategory(build_gim_config(), "50", "default"))

    assert [v.entry_key for v in violations] == ["gim:10.50/code"]


def test_default_99_rejects_code_99_with_other_name() -> None:
    """Code 99 is reserved for the default subcategory."""
    violations = _run("default-99", add_subcategory(build_gim_config(), "99", "other"))

    assert [v.entry_key for v in violations] == ["gim:10.99/name"]


def test_default_baseline_reports_each_missing_field() -> None:
    """Each field the default subcategory requires, but another subcategory doesn't, is reported."""
    gim_config = build_gim_config(subcat_required=["user_name"])
    add_subcategory(gim_config, "99", "default", required_fields=["user_name", "event_outcome", "host_name"])

    violations = _run("default-baseline", gim_config)

    assert [v.entry_key for v in violations] == [
        "gim:10.00/required_fields/event_outcome",
        "gim:10.00/required_fields/host_name",
    ]


def test_default_baseline_counts_category_required_fields() -> None:
    """A field required at category level already covers the default's requirement."""
    gim_config = build_gim_config(category_required=["event_outcome"])
    add_subcategory(gim_config, "99", "default", required_fields=["event_outcome"])

    assert _run("default-baseline", gim_config) == []


def test_codes_rejects_duplicate_category_codes() -> None:
    """Two categories with the same code are both reported."""
    gim_config = build_gim_config()
    gim_config["gim"].update(build_gim_config(category_name="iam", subcat_name="user")["gim"])

    violations = _run("codes", gim_config)

    assert [(v.entry_key, v.message) for v in violations] == [
        ("gim:10/code", "category code 10 is also used by iam"),
        ("gim:10/code", "category code 10 is also used by authentication"),
    ]


@pytest.mark.parametrize("file_name", ["11.authentication.toml", "authentication.toml"])
def test_codes_rejects_file_prefix_mismatch(file_name: str) -> None:
    """The file name must start with the category code."""
    model = model_from(build_gim_config())
    model.category_files["authentication"] = f"src/sdm/infomodels/{file_name}"

    assert [v.entry_key for v in RULES["codes"](model)] == ["gim:10/file"]
