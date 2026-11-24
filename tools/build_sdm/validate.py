"""Structural validation and lint rules for SDM source data (build-sdm validate).

A violation fails only if it is new relative to a base ref; violations that already
exist there are warnings (ADR 0004). Without a base ref, every violation is an error.
A per-rule ratchet also fails the check when any rule's count goes up.
"""

import io
import subprocess
import tarfile
import tempfile
import tomllib
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from build_sdm.rules import RULES, SdmModel, Violation, run_rules
from build_sdm.rules.locate import add_lines
from build_sdm.runner import _load_and_transform_gim_config

__all__ = [
    "BaseRefError",
    "Comparison",
    "StructuralError",
    "check_tree",
    "compare",
    "format_github_annotations",
    "format_report",
    "format_step_summary",
    "load_model",
    "violations_at_ref",
]

SOURCE_SUFFIXES = (".toml", ".tml")


class StructuralError(Exception):
    """The SDM source failed to load: a TOML, model, restructuring or cross-reference error."""


class BaseRefError(Exception):
    """The base ref doesn't name a commit."""


def _source_files(repo_dir: Path, source_dir: str) -> tuple[dict[str, str], dict[str, str]]:
    """Map each GIM category and field schema entity to the repo-relative file that defines it.

    Args:
        repo_dir: Root of the tree being checked.
        source_dir: SDM source directory relative to repo_dir.

    Returns:
        (category name -> file, entity name -> file).
    """
    categories: dict[str, str] = {}
    entities: dict[str, str] = {}
    for path in sorted(p for p in (repo_dir / source_dir).rglob("*") if p.suffix in SOURCE_SUFFIXES):
        with path.open("rb") as f:
            data = tomllib.load(f)
        target = {"gim": categories, "field_schema": entities}.get(data.get("type", ""))
        if target is not None:
            rel = path.relative_to(repo_dir).as_posix()
            target.update((key, rel) for key in data if key != "type")
    return categories, entities


def load_model(repo_dir: Path, source_dir: str = "src/sdm") -> SdmModel:
    """Load SDM source the way build does, without running output plugins.

    Args:
        repo_dir: Root of the tree being checked.
        source_dir: SDM source directory relative to repo_dir.

    Returns:
        The loaded model.

    Raises:
        StructuralError: If the source fails to parse, validate or restructure.
    """
    try:
        gim_config = _load_and_transform_gim_config(repo_dir, {"global": {"sdm_source_dir": source_dir}})
        categories, entities = _source_files(repo_dir, source_dir)
    except (OSError, ValueError, TypeError) as e:
        raise StructuralError(str(e)) from e
    return SdmModel(
        gim=gim_config.get("gim", {}),
        field_schema=gim_config.get("field_schema", {}),
        category_files=categories,
        entity_files=entities,
    )


def check_tree(repo_dir: Path, source_dir: str = "src/sdm") -> list[Violation]:
    """Load a tree and run every rule on it.

    Args:
        repo_dir: Root of the tree being checked.
        source_dir: SDM source directory relative to repo_dir.

    Returns:
        The sorted violations, each with its source line where it can be located.

    Raises:
        StructuralError: If the source fails to load.
    """
    model = load_model(repo_dir, source_dir)
    return add_lines(run_rules(model), model, repo_dir)


def _git(repo_root: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    """Run a git command in repo_root, capturing output."""
    return subprocess.run(["git", "-C", str(repo_root), *args], capture_output=True, check=False)


def violations_at_ref(repo_root: Path, ref: str, source_dir: str = "src/sdm") -> list[Violation]:
    """Export source_dir at ref with git archive and run every rule on it.

    Args:
        repo_root: Repository to read ref from.
        ref: Any git revision naming a commit.
        source_dir: SDM source directory relative to the repository root.

    Returns:
        The sorted violations at ref.

    Raises:
        BaseRefError: If ref doesn't name a commit.
        StructuralError: If source_dir is missing at ref or fails to load there.
    """
    if _git(repo_root, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}").returncode != 0:
        raise BaseRefError(f'base ref "{ref}" is not a commit in {repo_root}')
    archive = _git(repo_root, "archive", "--format=tar", ref, "--", source_dir)
    if archive.returncode != 0:
        detail = archive.stderr.decode(errors="replace").strip()
        raise StructuralError(f"{source_dir} could not be exported at {ref}: {detail}")
    with tempfile.TemporaryDirectory(prefix="build-sdm-base-") as tmp:
        with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as tar:
            tar.extractall(tmp, filter="data")
        return check_tree(Path(tmp), source_dir)


def _rule_counts(violations: list[Violation]) -> Counter[str]:
    """Count violations per rule_id."""
    return Counter(v.rule_id for v in violations)


@dataclass(slots=True)
class Comparison:
    """Head violations split into new (errors) and existing (warnings), with per-rule counts.

    Attributes:
        errors: Violations not present at the base ref (all of them without one).
        warnings: Violations whose (rule_id, entry_key) is present at the base ref.
        head_counts: Violations per rule at head.
        base_counts: Violations per rule at the base ref, or None without one.
        base_problem: Why the base ref couldn't be checked, if it loaded with errors.
    """

    errors: list[Violation]
    warnings: list[Violation]
    head_counts: Counter[str]
    base_counts: Counter[str] | None = None
    base_problem: str | None = None
    increased: list[str] = field(default_factory=list)

    @property
    def failed(self) -> bool:
        """Return True if the check fails: any new violation or any rule count went up."""
        return bool(self.errors or self.increased)


def compare(
    head: list[Violation], base: list[Violation] | None, base_problem: str | None = None
) -> Comparison:
    """Classify head violations against the base ref's.

    Args:
        head: Violations at head.
        base: Violations at the base ref; None means no base ref, or one that failed to load
            (then every head violation is new).
        base_problem: Why the base ref failed to load, if it did.

    Returns:
        The comparison. The ratchet is applied only when base violations are known.
    """
    head_counts = _rule_counts(head)
    if base is None:
        return Comparison(errors=list(head), warnings=[], head_counts=head_counts, base_problem=base_problem)

    existing = {(v.rule_id, v.entry_key) for v in base}
    base_counts = _rule_counts(base)
    return Comparison(
        errors=[v for v in head if (v.rule_id, v.entry_key) not in existing],
        warnings=[v for v in head if (v.rule_id, v.entry_key) in existing],
        head_counts=head_counts,
        base_counts=base_counts,
        increased=[rule for rule in RULES if head_counts[rule] > base_counts[rule]],
    )


def _location(v: Violation) -> str:
    """Return "file:line", or just the file when the line is unknown."""
    return v.file if v.line is None else f"{v.file}:{v.line}"


def _line(level: str, v: Violation) -> str:
    """Format one violation as "LEVEL rule_id file[:line] entry_key: message"."""
    return f"{level} {v.rule_id} {_location(v)} {v.entry_key}: {v.message}"


def format_report(result: Comparison, base_ref: str | None) -> list[str]:
    """Format the comparison for the terminal: warnings, then errors, then a summary.

    Args:
        result: The comparison.
        base_ref: The base ref compared against, or None.

    Returns:
        Output lines.
    """
    lines = [_line("WARNING", v) for v in result.warnings]
    lines.extend(_line("ERROR", v) for v in result.errors)
    if result.base_problem:
        lines.append(
            f"NOTE base ref {base_ref} could not be checked, so every violation is new: {result.base_problem}"
        )
    base_counts = result.base_counts or Counter()
    for rule in result.increased:
        lines.append(
            f"ERROR ratchet {rule}: violations went up from {base_counts[rule]} "
            f"at {base_ref} to {result.head_counts[rule]}"
        )

    lines.append("")
    if result.base_counts is None:
        lines.append(f"{'rule':<18}{'count':>6}")
        lines.extend(f"{rule:<18}{result.head_counts[rule]:>6}" for rule in RULES)
    else:
        lines.append(f"{'rule':<18}{'base':>6}{'head':>6}")
        lines.extend(
            f"{rule:<18}{result.base_counts[rule]:>6}{result.head_counts[rule]:>6}" for rule in RULES
        )
    lines.append(f"{len(result.errors)} error(s), {len(result.warnings)} warning(s)")
    return lines


def _escape(value: str, *, prop: bool = False) -> str:
    """Escape a value for a GitHub Actions workflow command."""
    value = value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    if prop:
        value = value.replace(":", "%3A").replace(",", "%2C")
    return value


def _annotation_props(v: Violation) -> str:
    """Return the file, line (when known) and title properties of an annotation."""
    line = "" if v.line is None else f",line={v.line}"
    return f"file={_escape(v.file, prop=True)}{line},title={_escape(v.rule_id, prop=True)}"


def format_github_annotations(result: Comparison) -> list[str]:
    """Format errors and warnings as GitHub Actions ::error/::warning annotations.

    An annotation with a line shows inline in the PR diff; one without shows only on the
    Checks tab.
    """
    return [
        f"::{level} {_annotation_props(v)}::{_escape(f'{v.entry_key}: {v.message}')}"
        for level, violations in (("warning", result.warnings), ("error", result.errors))
        for v in violations
    ]


def format_step_summary(result: Comparison, base_ref: str | None) -> str:
    """Format the per-rule counts as a Markdown table for the GitHub job summary."""
    if result.base_counts is None:
        rows = ["| Rule | Violations |", "|---|---:|"]
        rows.extend(f"| `{rule}` | {result.head_counts[rule]} |" for rule in RULES)
    else:
        rows = [f"| Rule | {base_ref} | Head |", "|---|---:|---:|"]
        rows.extend(
            f"| `{rule}` | {result.base_counts[rule]} | {result.head_counts[rule]} |" for rule in RULES
        )
    summary = f"{len(result.errors)} error(s), {len(result.warnings)} warning(s)"
    return "\n".join(["## build-sdm validate", "", *rows, "", summary, ""])
