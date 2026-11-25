"""Compare a fresh build's output tree with the committed one (build-sdm check-generated)."""

import shlex
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
        committed: The committed output directory (e.g. Content/SDM).
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


def format_diff(diff: TreeDiff, committed: str, build_command: str = "uv run build-sdm build") -> str:
    """Describe a non-clean TreeDiff and how to fix it.

    The fix names the stale files individually rather than clearing the directory, so a
    misconfigured output_dir can never turn the suggested command into a broad delete.

    Args:
        diff: The differences found.
        committed: The committed output directory as shown to the user, e.g. its
            repo-relative path.
        build_command: The command that rebuilds the output with the same configuration.

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
    lines.append("Fix, from the repository root:")
    lines.append(f"  {build_command}")
    if diff.stale:
        # The build never deletes files, so stale ones must be removed explicitly.
        stale = " ".join(shlex.quote(f"{committed}/{p.as_posix()}") for p in diff.stale)
        lines.append(f"  git rm -- {stale}")
    lines.append(f"  then commit {shlex.quote(committed)}.")
    return "\n".join(lines)
