"""taplo formatting must never change what a TOML file means (F12).

Every file the repo's taplo.toml includes is copied to a temporary directory, formatted
there with taplo, and parsed again: the values must be identical. This covers the
Markdown in multiline strings and future taplo upgrades.
"""

import shutil
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

import pytest

# taplo builds an HTTP client at startup; macOS sandboxes that block the system
# configuration service make that panic before any formatting happens.
SANDBOX_PANIC = "system-configuration"


def _included_files(repo_root: Path) -> list[Path]:
    """Return every file matched by the include globs in taplo.toml, relative to repo_root."""
    with (repo_root / "taplo.toml").open("rb") as f:
        includes: list[str] = tomllib.load(f)["include"]
    return sorted({p.relative_to(repo_root) for pattern in includes for p in repo_root.glob(pattern)})


def _parse(path: Path) -> dict[str, Any]:
    """Parse a TOML file."""
    with path.open("rb") as f:
        return tomllib.load(f)


def test_include_globs_cover_the_sdm_source(repo_root: Path) -> None:
    """taplo.toml includes every SDM source file and the build-sdm configs."""
    files = {p.as_posix() for p in _included_files(repo_root)}

    assert {p.relative_to(repo_root).as_posix() for p in (repo_root / "src/sdm").rglob("*.toml")} <= files
    assert "tools/build_sdm/configs/build_sdm.toml" in files


def test_formatting_preserves_parsed_values(repo_root: Path, tmp_path: Path) -> None:
    """Formatting a copy of every included file leaves each one parsing to the same values."""
    files = _included_files(repo_root)
    shutil.copy(repo_root / "taplo.toml", tmp_path / "taplo.toml")
    for rel in files:
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(repo_root / rel, tmp_path / rel)

    taplo = Path(sys.executable).with_name("taplo")
    result = subprocess.run([str(taplo), "fmt"], cwd=tmp_path, capture_output=True, text=True, check=False)
    if result.returncode != 0 and SANDBOX_PANIC in result.stderr:
        pytest.skip(f"taplo cannot start in this environment: {result.stderr.strip().splitlines()[0]}")
    assert result.returncode == 0, result.stderr

    changed = [rel.as_posix() for rel in files if _parse(tmp_path / rel) != _parse(repo_root / rel)]
    assert changed == []
