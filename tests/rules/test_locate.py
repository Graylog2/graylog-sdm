"""Source lines for violations (F19): entry_key -> line in the TOML file, for inline annotations."""

from pathlib import Path

import pytest

from build_sdm.rules import SdmModel, Violation
from build_sdm.rules.locate import SourceIndex, add_lines
from build_sdm.validate import compare, format_github_annotations, format_report

GIM_FILE = "src/sdm/infomodels/10.authentication.toml"
SCHEMA_FILE = "src/sdm/schema/user.toml"

GIM = '''type = "gim"

[authentication]
name = "authentication"
code = "10"
description = """
Authentication events.
[not.a.table]
name = "not a key"
"""
required_fields = [
    "user_name",
    'user_domain',
]
optional_fields = ["source_ip", "user_*"]

[[authentication.summaries]]
template_id = "default"
title = "Default"
description = "Default view"

[[authentication.summaries]]
template_id = "extended"
title = "Extended"
description = "Extended view"

[[authentication.indicators]]
type = "eventOutcome"
title = "Outcome"
description = "Outcome indicator"

[authentication.subcategories]

[authentication.subcategories.05]
name = "credential validation"
description = "Checks credentials."
required_fields = ['event_outcome']
summary.title = "credential validation"

[authentication.subcategories.05.event_type_codes]
00.name = "credential validation"
00.description = "Validation."

[authentication.subcategories.10.event_type_codes.01]
name = "Bad Name"
description = "Header form."
'''

SCHEMA = '''type = "field_schema"

[user]
description = """
User fields.
"""
entity_type = "top"

[[user.fields]]
field_suffix = "domain"
field_type = "keyword"
description = "Domain."

[[user.fields]]
field_suffix = "name"
field_type = "keyword"
description = "Name."
'''


def _line(text: str, needle: str, after: str | None = None) -> int:
    """Return the 1-based line of the first line equal to needle (after the line equal to after)."""
    lines = text.splitlines()
    start = lines.index(after) + 1 if after is not None else 0
    return lines.index(needle, start) + 1


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A tree holding the GIM and schema files above."""
    for rel, text in ((GIM_FILE, GIM), (SCHEMA_FILE, SCHEMA)):
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return tmp_path


@pytest.fixture
def model() -> SdmModel:
    """A model whose only category is authentication (code 10) in GIM_FILE."""
    return SdmModel(
        gim={"authentication": {"code": "10"}},
        field_schema={"user": {}},
        category_files={"authentication": GIM_FILE},
        entity_files={"user": SCHEMA_FILE},
    )


def _locate(repo: Path, model: SdmModel, entry_key: str, file: str = GIM_FILE) -> int | None:
    """Return the line add_lines finds for one violation."""
    [located] = add_lines([Violation("rule", entry_key, "message", file)], model, repo)
    return located.line


@pytest.mark.parametrize(
    ("entry_key", "needle", "after"),
    [
        ("gim:10/name", 'name = "authentication"', None),
        ("gim:10/description", 'description = """', None),
        ("gim:10.05/name", 'name = "credential validation"', None),
        ("gim:10.05/summary/title", 'summary.title = "credential validation"', None),
        ("gim:10.05.00/name", '00.name = "credential validation"', None),
        ("gim:10.10.01/name", 'name = "Bad Name"', None),
        ("gim:10/summaries/extended/title", 'title = "Extended"', None),
        ("gim:10/indicators/eventOutcome/description", 'description = "Outcome indicator"', None),
        ("gim:10/required_fields/user_domain", "    'user_domain',", None),
        ("gim:10.05/required_fields/event_outcome", "required_fields = ['event_outcome']", None),
        ("gim:10/optional_fields/user_*", 'optional_fields = ["source_ip", "user_*"]', None),
    ],
)
def test_gim_entries(repo: Path, model: SdmModel, entry_key: str, needle: str, after: str | None) -> None:
    """Categories, subcategories, event types, array elements and list items get their own line."""
    assert _locate(repo, model, entry_key) == _line(GIM, needle, after)


def test_schema_field_is_found_by_suffix(repo: Path, model: SdmModel) -> None:
    """A schema field's description is found in the [[user.fields]] element with that field_suffix."""
    line = _locate(repo, model, "schema:user/fields/name/description", SCHEMA_FILE)

    assert line == _line(SCHEMA, 'description = "Name."')


def test_schema_entity_description(repo: Path, model: SdmModel) -> None:
    """An entity's own multiline description is found at its key."""
    assert _locate(repo, model, "schema:user/description", SCHEMA_FILE) == _line(SCHEMA, 'description = """')


def test_attribute_without_a_line_falls_back_to_its_table(repo: Path, model: SdmModel) -> None:
    """A subcategory's code is its table name, so the violation points at the table header."""
    line = _locate(repo, model, "gim:10.05/code")

    assert line == _line(GIM, "[authentication.subcategories.05]")


def test_missing_list_item_falls_back_to_the_key(repo: Path, model: SdmModel) -> None:
    """A list item that isn't in the array resolves to the array's key."""
    assert _locate(repo, model, "gim:10/required_fields/nope") == _line(GIM, "required_fields = [")


def test_text_inside_a_multiline_string_is_not_indexed() -> None:
    """Header- and key-like lines inside a multiline string are content, not TOML structure."""
    index = SourceIndex.from_text(GIM)

    assert ("not", "a", "table") not in index.spans
    assert index.find(("authentication", "name")) == _line(GIM, 'name = "authentication"')


def test_unicode_line_separators_are_not_line_breaks() -> None:
    """U+2028 and U+0085 inside a string don't shift the numbering of later lines."""
    text = '[t]\ndescription = "one\u2028two\x85three"\nname = "x"\n'

    assert SourceIndex.from_text(text).find(("t", "name")) == 3


def test_crlf_line_endings() -> None:
    """CRLF files number the same as LF files."""
    text = '[t]\r\ndescription = """\r\nText.\r\n"""\r\nname = "x"\r\n'

    assert SourceIndex.from_text(text).find(("t", "name")) == 5


def test_escaped_delimiter_does_not_end_a_multiline_string() -> None:
    """An escaped triple quote inside a basic multiline string isn't its end."""
    text = '[t]\ndescription = """\nQuote: \\"""\nname = "inside the string"\n"""\nname = "real"\n'
    index = SourceIndex.from_text(text)

    assert index.find(("t", "name")) == 6
    assert index.spans[("t", "description")] == (2, 5)


def test_escaped_backslash_before_delimiter_still_ends_the_string() -> None:
    """An escaped backslash followed by a triple quote ends the string."""
    text = '[t]\ndescription = """\nPath: C:\\\\"""\nname = "real"\n'

    assert SourceIndex.from_text(text).find(("t", "name")) == 4


def test_comments_in_arrays_are_not_items() -> None:
    """A quoted name in a comment doesn't match; a name found only in a comment falls back to the key."""
    text = '[t]\nrequired_fields = [\n    # was "user_name", "user_id"\n    "user_name",\n]\n'
    index = SourceIndex.from_text(text)

    assert index.find(("t", "required_fields", "user_name")) == 4
    assert index.find(("t", "required_fields", "user_id")) == 2


@pytest.mark.parametrize(
    ("entry_key", "file"),
    [
        ("gim:99/name", GIM_FILE),
        ("schema:group/description", SCHEMA_FILE),
        ("gim:10/name", "src/sdm/infomodels/missing.toml"),
        ("gim:10/name", "<unknown>"),
        ("other:10/name", GIM_FILE),
    ],
)
def test_unlocatable_entries_get_no_line(repo: Path, model: SdmModel, entry_key: str, file: str) -> None:
    """An unknown category or entity, a missing file, or an unknown key scheme leaves line None."""
    assert _locate(repo, model, entry_key, file) is None


def test_moved_line_keeps_a_violation_existing() -> None:
    """A violation whose line moved since the base ref is still existing: line isn't identity."""
    base = [Violation("naming", "gim:10/name", "message", GIM_FILE, line=3)]
    head = [Violation("naming", "gim:10/name", "message", GIM_FILE, line=9)]

    result = compare(head, base)

    assert result.warnings == head
    assert not result.errors
    assert not result.failed


def test_formats_include_the_line_when_known() -> None:
    """The report shows file:line and the annotation gets line=; without a line, neither does."""
    located = Violation("naming", "gim:10/name", "message", GIM_FILE, line=7)
    unlocated = Violation("codes", "gim:10/file", "message", GIM_FILE)
    result = compare([located, unlocated], None)

    report = format_report(result, None)
    assert f"ERROR naming {GIM_FILE}:7 gim:10/name: message" in report
    assert f"ERROR codes {GIM_FILE} gim:10/file: message" in report
    assert format_github_annotations(result) == [
        f"::error file={GIM_FILE},line=7,title=naming::gim:10/name: message",
        f"::error file={GIM_FILE},title=codes::gim:10/file: message",
    ]
