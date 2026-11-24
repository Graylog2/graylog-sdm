"""Find the source line of each violation, so CI annotations show inline in PR diffs.

Lines are looked up after the rules run, from the violation's file and entry_key, by
scanning the TOML text. The loader isn't involved: it normalizes to plain values and
drops positions. A line is for display only; entry_key stays the violation's identity.
"""

import re
from dataclasses import dataclass, field, replace
from pathlib import Path

from build_sdm.rules.model import UNKNOWN_FILE, SdmModel, Violation

__all__ = ["SourceIndex", "add_lines"]

_PART = r"""(?:[A-Za-z0-9_-]+|"[^"]*"|'[^']*')"""
_HEADER = re.compile(rf"^\s*(\[\[?)\s*({_PART}(?:\s*\.\s*{_PART})*)\s*\]\]?\s*(?:#.*)?$")
_KEY = re.compile(rf"^\s*({_PART}(?:\s*\.\s*{_PART})*)\s*=\s*(.*)$")
_PARTS = re.compile(_PART)
_QUOTED = re.compile(r""""(?:[^"\\]|\\.)*"|'[^']*'""")
_SCALAR = re.compile(r"""^"((?:[^"\\]|\\.)*)"|^'([^']*)'""")
# A string token, or the # that starts a comment (only reached outside strings).
_TOKEN = re.compile(r""""(?:[^"\\]|\\.)*"|'[^']*'|#""")
# The end of a multiline string. In a basic string, a """ preceded by an odd number of
# backslashes is an escaped quote, not the end; literal strings have no escapes.
_CLOSING = {
    '"""': re.compile(r'(?:^|[^\\])(?:\\\\)*"""'),
    "'''": re.compile("'''"),
}

# Keys whose value identifies an element of an array of tables, e.g. [[agent.fields]].
ID_KEYS = ("field_suffix", "template_id", "type")

KeyPath = tuple[str, ...]


def _split(dotted: str) -> KeyPath:
    """Split a dotted TOML key or header into its parts, without quotes."""
    return tuple(p.strip("\"'") for p in _PARTS.findall(dotted))


def _physical_lines(text: str) -> list[str]:
    """Split text into source lines on LF only, dropping a CR before it.

    str.splitlines() would also split on characters such as U+2028, which can appear
    inside TOML strings and are not line breaks in the file.
    """
    return [line.removesuffix("\r") for line in text.split("\n")]


def _bracket_depth(text: str) -> int:
    """Return the net count of [ over ] in text, ignoring strings and comments."""
    code = _QUOTED.sub("", text).split("#", 1)[0]
    return code.count("[") - code.count("]")


@dataclass(slots=True)
class SourceIndex:
    """Line positions of the tables, keys and array items in one TOML file.

    Attributes:
        spans: Full dotted path -> (first line, last line), for tables and keys. Lines are 1-based.
        arrays: Array-of-tables path -> its element paths, in order.
        values: Full dotted path -> single-line string value.
        array_keys: Paths of keys whose value is an array, for finding list items.
        text: The file's lines.
    """

    spans: dict[KeyPath, tuple[int, int]] = field(default_factory=dict)
    arrays: dict[KeyPath, list[KeyPath]] = field(default_factory=dict)
    values: dict[KeyPath, str] = field(default_factory=dict)
    array_keys: set[KeyPath] = field(default_factory=set)
    text: list[str] = field(default_factory=list)

    @classmethod
    def from_text(cls, text: str) -> "SourceIndex":
        """Index TOML text line by line, skipping the contents of multiline strings and arrays."""
        index = cls(text=_physical_lines(text))
        table: KeyPath = ()
        lines = index.text
        i = 0
        while i < len(lines):
            line = lines[i]
            number = i + 1
            i += 1
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            if header := _HEADER.match(line):
                path = _split(header.group(2))
                if header.group(1) == "[[":
                    elements = index.arrays.setdefault(path, [])
                    path = (*path, f"[{len(elements)}]")
                    elements.append(path)
                table = path
                index._record(table, number, number)
                continue
            key = _KEY.match(line)
            if key is None:
                continue
            path = (*table, *_split(key.group(1)))
            value = key.group(2)
            end = number
            delimiter = next((d for d in ('"""', "'''") if value.startswith(d)), None)
            if delimiter is not None:
                closing = _CLOSING[delimiter]
                if not closing.search(value[len(delimiter) :]):
                    while i < len(lines) and not closing.search(lines[i]):
                        i += 1
                    i += 1
                    end = min(i, len(lines))
            elif value.startswith("["):
                index.array_keys.add(path)
                depth = _bracket_depth(value)
                while depth > 0 and i < len(lines):
                    depth += _bracket_depth(lines[i])
                    i += 1
                end = i if i > number else number
            elif scalar := _SCALAR.match(value):
                index.values[path] = scalar.group(1) if scalar.group(1) is not None else scalar.group(2)
            index._record(path, number, end)
        return index

    def _record(self, path: KeyPath, first: int, last: int) -> None:
        """Record a span for path, and for any parent tables it implies that aren't recorded yet."""
        for depth in range(1, len(path)):
            self.spans.setdefault(path[:depth], (first, first))
        self.spans[path] = (first, last)

    def _element(self, array: KeyPath, ident: str) -> KeyPath | None:
        """Return the element of an array of tables whose ID key equals ident."""
        for element in self.arrays.get(array, []):
            if any(self.values.get((*element, k)) == ident for k in ID_KEYS):
                return element
        return None

    def _item_line(self, path: KeyPath, item: str) -> int | None:
        """Return the line of a string item within an array-valued key, ignoring comments."""
        first, last = self.spans[path]
        for number in range(first, last + 1):
            line = self.text[number - 1]
            if number == first:
                line = line.split("=", 1)[1]
            for token in _TOKEN.finditer(line):
                if token.group() == "#":
                    break
                if token.group()[1:-1] == item:
                    return number
        return None

    def find(self, segments: KeyPath) -> int | None:
        """Return the line for a path of keys, array-element IDs and list items.

        Walks the path as far as the file defines it and returns the line of the deepest
        part found, so an attribute with no line of its own (such as a subcategory's code,
        which is its table name) resolves to its table. Returns None if even the first
        segment isn't found.

        Args:
            segments: e.g. ("agent", "fields", "ephemeral_id", "description").

        Returns:
            The 1-based line, or None.
        """
        path: KeyPath = ()
        line: int | None = None
        i = 0
        while i < len(segments):
            candidate = (*path, segments[i])
            if candidate in self.arrays and i + 1 < len(segments):
                element = self._element(candidate, segments[i + 1])
                if element is None:
                    break
                path, i = element, i + 2
            elif candidate in self.spans:
                path, i = candidate, i + 1
            elif path in self.array_keys:
                return self._item_line(path, segments[i]) or line
            else:
                break
            line = self.spans[path][0]
        return line


def _segments(violation: Violation, model: SdmModel) -> KeyPath | None:
    """Translate an entry_key into a path through the TOML file, or None if it can't be."""
    scheme, _, rest = violation.entry_key.partition(":")
    head, *attrs = rest.split("/")
    if scheme == "schema":
        return (head, *attrs)
    if scheme != "gim":
        return None

    category_code, *codes = head.split(".")
    names = [
        name
        for name, category in model.gim.items()
        if category.get("code") == category_code and model.category_file(name) == violation.file
    ]
    if len(names) != 1:
        return None
    path: KeyPath = (names[0],)
    for table, code in zip(("subcategories", "event_type_codes"), codes, strict=False):
        path = (*path, table, code)
    return (*path, *attrs)


def add_lines(violations: list[Violation], model: SdmModel, repo_dir: Path) -> list[Violation]:
    """Return the violations with line set wherever the entry can be found in its file.

    Args:
        violations: Violations from the rules.
        model: The model the rules ran on, to map category codes to table names.
        repo_dir: Root of the tree the violation files are relative to.

    Returns:
        The violations, in the same order. An entry that can't be located keeps line None.
    """
    indexes: dict[str, SourceIndex | None] = {}
    located = []
    for v in violations:
        if v.file not in indexes:
            source = repo_dir / v.file
            indexes[v.file] = (
                SourceIndex.from_text(source.read_text(encoding="utf-8"))
                if v.file != UNKNOWN_FILE and source.is_file()
                else None
            )
        index = indexes[v.file]
        segments = _segments(v, model)
        line = index.find(segments) if index is not None and segments is not None else None
        located.append(replace(v, line=line) if line is not None else v)
    return located
