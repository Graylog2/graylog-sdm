"""Compare a fresh build's output tree with the committed one (build-sdm check-generated)."""

from dataclasses import dataclass, field
from pathlib import Path

__all__ = ["TreeDiff", "compare_trees", "format_diff"]


@dataclass(slots=True)
class TreeDiff:
    """Differences between the committed tree and a fresh build, as relative paths.

    Attributes:
        changed: Files in both trees whose bytes differ.
        stale: Files only in the committed tree; the build no longer produces them.
        missing: Files only in the fresh build; they were never committed.
    """

    changed: list[Path] = field(default_factory=list)
    stale: list[Path] = field(default_factory=list)
    missing: list[Path] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        """Return True if the trees are identical."""
        return not (self.changed or self.stale or self.missing)


def _files(directory: Path) -> set[Path]:
    """Return every file under directory, relative to it.

    Args:
        directory: Directory to list; may not exist.

    Returns:
        Relative paths of all files, or an empty set if directory doesn't exist.
    """
    if not directory.is_dir():
        return set()
    return {p.relative_to(directory) for p in directory.rglob("*") if p.is_file()}


def compare_trees(committed: Path, fresh: Path) -> TreeDiff:
    """Compare two directory trees byte for byte, in both directions.

    Args:
        committed: The committed output directory (e.g. generated/MadcapHtmlOutput).
        fresh: A fresh build of the same output.

    Returns:
        The changed, stale and missing files, each sorted.
    """
    committed_files, fresh_files = _files(committed), _files(fresh)
    changed = [
        rel
        for rel in committed_files & fresh_files
        if (committed / rel).read_bytes() != (fresh / rel).read_bytes()
    ]
    return TreeDiff(
        changed=sorted(changed),
        stale=sorted(committed_files - fresh_files),
        missing=sorted(fresh_files - committed_files),
    )


def format_diff(diff: TreeDiff, committed: str) -> str:
    """Describe a non-clean TreeDiff and how to fix it.

    Args:
        diff: The differences found.
        committed: The committed output directory as shown to the user, e.g. its
            repo-relative path.

    Returns:
        A multi-line report.
    """
    lines = [f"{committed} is out of date with the source:"]
    sections = [
        ("changed (differs from a fresh build)", diff.changed),
        ("stale (no longer built; delete it)", diff.stale),
        ("missing (built but not committed)", diff.missing),
    ]
    for title, paths in sections:
        if paths:
            lines.append(f"  {title}:")
            lines.extend(f"    {p.as_posix()}" for p in paths)
    # The build never deletes files, so clear the directory first to drop stale ones.
    lines.append(f"Fix: rm -rf '{committed}' && uv run build-sdm build, then commit '{committed}'.")
    return "\n".join(lines)
