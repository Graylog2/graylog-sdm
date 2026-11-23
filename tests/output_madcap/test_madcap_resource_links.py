"""Generated pages link resources relative to the page, never from the site root (F13)."""

import re
from pathlib import Path
from typing import Any

import pytest

from build_sdm.output_plugins.madcap_html_output import MadcapHtmlOutput
from build_sdm.runner import _load_and_transform_gim_config

RESOURCE_REF = re.compile(r"""(?:href="|url\(')([^"']*\.css)""")


@pytest.fixture
def gim_config(repo_root: Path) -> dict[str, Any]:
    """Load the real SDM source and the MadCap page config, as the build does."""
    return _load_and_transform_gim_config(
        repo_root, {"global": {"sdm_source_dir": "src/sdm"}}, repo_root / "tools/build_sdm/configs"
    )


def test_stylesheet_links_are_relative(tmp_path: Path, gim_config: dict[str, Any]) -> None:
    """Every stylesheet reference starts with '../', including the top-level index pages."""
    MadcapHtmlOutput().generate(gim_config, tmp_path)

    pages = sorted(tmp_path.rglob("*.html"))
    assert any(p.name == "Graylog_Schema_entities.html" for p in pages)

    refs = {
        (p.relative_to(tmp_path).as_posix(), ref)
        for p in pages
        for ref in RESOURCE_REF.findall(p.read_text())
    }
    assert refs
    assert [r for r in refs if not r[1].startswith("../")] == []
