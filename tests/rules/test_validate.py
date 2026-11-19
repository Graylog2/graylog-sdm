"""Tests for build-sdm validate: loading, the base-ref comparison, the ratchet and output formats."""

import re
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest

from build_sdm import cli
from build_sdm.rules import Violation
from build_sdm.validate import (
    BaseRefError,
    StructuralError,
    check_tree,
    compare,
    format_github_annotations,
    format_report,
    format_step_summary,
    violations_at_ref,
)

GIM_FILE = "src/sdm/infomodels/10.authentication.toml"

CONFIG = 'type = "config"\n\n[field_schema_config]\nallowed_field_types = ["keyword"]\n'
SCHEMA = """type = "field_schema"

[user]
description = "User fields."
entity_type = "top"

[[user.fields]]
field_suffix = "name"
field_type = "keyword"
description = "User name."
"""


def _subcategory(code: str, name: str) -> str:
    """Return the TOML for one subcategory with one conforming event type."""
    return f"""
[authentication.subcategories.{code}]
name = "{name}"
description = "Subcategory."

[authentication.subcategories.{code}.event_type_codes]
00.name = "{re.sub("[^a-z]+", "_", name.lower()).strip("_")}_event"
00.description = "Event type."
"""


def _gim(*subcategories: tuple[str, str]) -> str:
    """Return the TOML for the authentication category with the given (code, name) subcategories."""
    head = """type = "gim"

[authentication]
name = "authentication"
code = "10"
description = "Authentication."
required_fields = ["user_name"]
"""
    return head + "".join(_subcategory(code, name) for code, name in subcategories)


def _git(repo: Path, *args: str) -> None:
    """Run a git command in repo, failing the test on error."""
    # CI runners have no git identity, and a developer's signing setup must not apply.
    identity = ["-c", "user.name=build-sdm tests", "-c", "user.email=tests@example.invalid"]
    signing = ["-c", "commit.gpgsign=false"]
    subprocess.run(["git", "-C", str(repo), *identity, *signing, *args], check=True, capture_output=True)


def _write_gim(repo: Path, text: str) -> None:
    """Replace the authentication infomodel in repo."""
    (repo / GIM_FILE).write_text(text, encoding="utf-8")


def _commit(repo: Path) -> None:
    """Commit everything in repo."""
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "update")


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """A git repo with a minimal SDM whose base commit has one existing naming violation."""
    for name, value in {
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "test@example.com",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "test@example.com",
    }.items():
        monkeypatch.setenv(name, value)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)

    repo = tmp_path / "repo"
    for rel, text in {
        "pyproject.toml": '[project]\nname = "build-sdm"\n',
        "src/sdm/config/field_schema.config.toml": CONFIG,
        "src/sdm/schema/user.toml": SCHEMA,
        GIM_FILE: _gim(("00", "logon"), ("05", "credential validation")),
    }.items():
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    _git(repo, "init", "-q", "-b", "main")
    _commit(repo)
    monkeypatch.chdir(repo)
    yield repo


def _validate(*args: str) -> int:
    """Run build-sdm validate with the given arguments."""
    return cli.main(["validate", "-ll", "critical", *args])


def test_existing_violation_is_a_warning(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Against a base ref that already has the violation, it is a warning and the check passes."""
    assert _validate("--base-ref", "HEAD") == 0

    out = capsys.readouterr().out
    assert f"WARNING naming {GIM_FILE} gim:10.05/name:" in out
    assert "0 error(s), 1 warning(s)" in out


def test_without_base_ref_every_violation_is_an_error(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """With no base ref, existing violations are errors too."""
    assert _validate() == 1
    assert "1 error(s), 0 warning(s)" in capsys.readouterr().out


def test_new_bad_name_is_one_error(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Adding a subcategory named Bad-Name fails with exactly one new naming error."""
    _write_gim(repo, _gim(("00", "logon"), ("05", "credential validation"), ("10", "Bad-Name")))

    assert _validate("--base-ref", "HEAD") == 1

    out = capsys.readouterr().out
    assert f"ERROR naming {GIM_FILE} gim:10.10/name:" in out
    assert "1 error(s), 1 warning(s)" in out


def test_rename_keeps_existing_violation_a_warning(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """entry_keys use codes, so renaming a violating subcategory keeps its violation existing (F5)."""
    _write_gim(repo, _gim(("00", "logon"), ("05", "credential check")))

    assert _validate("--base-ref", "HEAD") == 0
    assert "WARNING naming" in capsys.readouterr().out


def test_renumber_makes_violation_new(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Moving a violating subcategory to a new code changes its key, so it is a new error."""
    _write_gim(repo, _gim(("00", "logon"), ("06", "credential validation")))

    assert _validate("--base-ref", "HEAD") == 1
    assert "ERROR naming" in capsys.readouterr().out


def test_fixing_a_violation_passes(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Fixing the existing violation leaves nothing to report."""
    _write_gim(repo, _gim(("00", "logon"), ("05", "credential_validation")))

    assert _validate("--base-ref", "HEAD") == 0
    assert "0 error(s), 0 warning(s)" in capsys.readouterr().out


def test_unloadable_base_makes_every_violation_new(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """If the base tree fails to load, every head violation is an error, and the output says why."""
    _write_gim(repo, "type = \n")
    _commit(repo)
    _write_gim(repo, _gim(("00", "logon"), ("05", "credential validation")))

    assert _validate("--base-ref", "HEAD") == 1

    out = capsys.readouterr().out
    assert "NOTE base ref HEAD could not be checked" in out
    assert "ERROR naming" in out


def test_missing_source_dir_at_base_makes_every_violation_new(repo: Path) -> None:
    """A base ref from before src/sdm existed can't be checked; that is a structural problem, not a crash."""
    _git(repo, "checkout", "-q", "--orphan", "empty")
    _git(repo, "rm", "-rq", "--cached", ".")
    _git(repo, "commit", "-q", "--allow-empty", "-m", "empty")

    with pytest.raises(StructuralError, match="could not be exported"):
        violations_at_ref(repo, "empty")


def test_unknown_base_ref_fails(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A base ref that isn't a commit is an error, not an empty baseline."""
    with pytest.raises(BaseRefError):
        violations_at_ref(repo, "no-such-ref")

    assert _validate("--base-ref", "no-such-ref") == 1
    assert 'base ref "no-such-ref" is not a commit' in capsys.readouterr().out


def test_structural_error_at_head_fails(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Source that doesn't load is reported as a structural error."""
    _write_gim(repo, _gim(("00", "logon")).replace('code = "10"', 'code = "ten"'))

    with pytest.raises(StructuralError):
        check_tree(repo)
    assert _validate("--base-ref", "HEAD") == 1
    assert "ERROR structural src/sdm" in capsys.readouterr().out


def test_github_annotations_and_step_summary(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Under GitHub Actions, violations become annotations and the counts go to the job summary."""
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))

    assert _validate("--base-ref", "HEAD") == 0

    assert f"::warning file={GIM_FILE},title=naming::gim:10.05/name: " in capsys.readouterr().out
    assert "| `naming` | 1 | 1 |" in summary.read_text(encoding="utf-8")


def _v(rule_id: str, key: str) -> Violation:
    """Build a violation with a fixed file and message."""
    return Violation(rule_id, key, "message", "src/sdm/x.toml")


def test_ratchet_fails_when_a_rule_count_goes_up() -> None:
    """A rule whose count rises fails the check even if every key already existed (F5)."""
    base = [_v("codes", "gim:10/code"), _v("codes", "gim:10/code")]
    head = [*base, _v("codes", "gim:10/code")]

    result = compare(head, base)

    assert result.errors == []
    assert result.increased == ["codes"]
    assert result.failed
    assert "ERROR ratchet codes: violations went up from 2 at main to 3" in format_report(result, "main")


def test_report_format_and_counts() -> None:
    """Lines are "LEVEL rule_id file entry_key: message", warnings first, then counts and a summary."""
    result = compare(
        [_v("naming", "gim:10.05/name"), _v("naming", "gim:10.06/name")], [_v("naming", "gim:10.05/name")]
    )

    lines = format_report(result, "main")

    assert lines[:2] == [
        "WARNING naming src/sdm/x.toml gim:10.05/name: message",
        "ERROR naming src/sdm/x.toml gim:10.06/name: message",
    ]
    assert "naming                 1     2" in lines
    assert lines[-1] == "1 error(s), 1 warning(s)"


def test_annotation_values_are_escaped() -> None:
    """Newlines, percent signs and property separators can't break the workflow command."""
    result = compare([Violation("naming", "gim:10/name", "50%\nbad", "a,b:c.toml")], None)

    assert format_github_annotations(result) == [
        "::error file=a%2Cb%3Ac.toml,title=naming::gim:10/name: 50%25%0Abad"
    ]


def test_step_summary_without_base_lists_head_counts() -> None:
    """Without a base ref, the summary table has one count column."""
    summary = format_step_summary(compare([_v("naming", "gim:10/name")], None), None)

    assert "| `naming` | 1 |" in summary
