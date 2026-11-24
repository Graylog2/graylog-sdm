"""Guard an explicitly chosen output directory against overwriting files the tool didn't write."""

from pathlib import Path

__all__ = ["MARKER_NAME", "UnsafeOutputDirError", "check_output_dir", "mark_output_dir", "paths_overlap"]

MARKER_NAME = ".build-sdm-output"

_MARKER_TEXT = (
    "This directory holds build-sdm output. build-sdm overwrites files here on every build.\n"
    "Delete this file to stop build-sdm writing here without --force.\n"
)

# Files the OS file manager adds to directories it shows (macOS Finder, Windows Explorer).
# The build never writes these names, so they can't be overwritten, and they don't make a
# directory count as non-empty.
_OS_METADATA_NAMES = frozenset({".DS_Store", "Thumbs.db", "desktop.ini"})


class UnsafeOutputDirError(Exception):
    """Raised when an output directory holds files build-sdm didn't write."""


def check_output_dir(directory: Path, force: bool = False) -> bool:
    """Check that build output may be written to directory.

    A directory is safe when it doesn't exist, is empty, or holds the marker file
    build-sdm writes into directories it created output in. A directory holding only OS
    metadata files (.DS_Store, Thumbs.db, desktop.ini) counts as empty; a subdirectory with
    one of those names does not.

    Args:
        directory: The output directory.
        force: Allow a non-empty directory without the marker.

    Returns:
        True if the directory should be marked after the check: it doesn't exist yet or is empty.

    Raises:
        UnsafeOutputDirError: directory exists and isn't a directory, or it is non-empty, has no
            marker, and force is False.
    """
    if not directory.exists():
        return True
    if not directory.is_dir():
        raise UnsafeOutputDirError(f"{directory} exists and is not a directory")
    if all(entry.name in _OS_METADATA_NAMES and entry.is_file() for entry in directory.iterdir()):
        return True
    if (directory / MARKER_NAME).is_file() or force:
        return False
    raise UnsafeOutputDirError(
        f"{directory} is not empty and has no {MARKER_NAME} marker, so it may hold files "
        "build-sdm didn't write, which the build would overwrite. Use an empty directory, "
        "or pass --force to write there anyway."
    )


def paths_overlap(a: Path, b: Path) -> bool:
    """Return True if a and b are the same directory or one contains the other.

    Args:
        a: An absolute, resolved path.
        b: An absolute, resolved path.
    """
    return a == b or a in b.parents or b in a.parents


def mark_output_dir(directory: Path) -> None:
    """Create directory if needed and write the marker file into it.

    Args:
        directory: The output directory.
    """
    directory.mkdir(parents=True, exist_ok=True)
    (directory / MARKER_NAME).write_text(_MARKER_TEXT, encoding="utf-8")
