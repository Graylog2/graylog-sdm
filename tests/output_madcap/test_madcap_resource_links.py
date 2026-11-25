"""Generated pages link resources relative to the page (F13), all at one configured depth (F20)."""

import re
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from build_sdm.output_plugins.madcap_html_output import MadcapHtmlOutput
from build_sdm.output_plugins.madcap_html_output.models import (
    DEFAULT_RESOURCES_PATH,
    MadcapHtmlOutputConfig,
)
from build_sdm.runner import _load_and_transform_gim_config

RESOURCE_REF = re.compile(r"""(?:href="|url\(')([^"']*\.css)""")


@pytest.fixture
def gim_config(repo_root: Path) -> dict[str, Any]:
    """Load the real SDM source and the MadCap page config, as the build does."""
    return _load_and_transform_gim_config(
        repo_root, {"global": {"sdm_source_dir": "src/sdm"}}, repo_root / "tools/build_sdm/configs"
    )


def _stylesheet_refs(output_dir: Path) -> set[tuple[str, str]]:
    """Return (page, stylesheet reference) pairs for every generated page."""
    pages = sorted(output_dir.rglob("*.html"))
    assert any(p.name == "Graylog_Schema_entities.html" for p in pages)
    assert any(p.name == "Graylog_Entity_Categories.html" for p in pages)
    refs = {
        (p.relative_to(output_dir).as_posix(), ref)
        for p in pages
        for ref in RESOURCE_REF.findall(p.read_text())
    }
    assert refs
    return refs


def test_stylesheet_links_are_relative(tmp_path: Path, gim_config: dict[str, Any]) -> None:
    """Every stylesheet reference starts with '../', including the top-level index pages."""
    MadcapHtmlOutput().generate(gim_config, tmp_path, MadcapHtmlOutputConfig())

    assert [r for r in _stylesheet_refs(tmp_path) if not r[1].startswith("../")] == []


def test_every_page_links_resources_at_one_depth(tmp_path: Path, gim_config: dict[str, Any]) -> None:
    """Page links and table styles all use the default resources_path."""
    MadcapHtmlOutput().generate(gim_config, tmp_path, MadcapHtmlOutputConfig())

    prefix = f"{DEFAULT_RESOURCES_PATH}/"
    assert [r for r in _stylesheet_refs(tmp_path) if not r[1].startswith(prefix)] == []


def test_configured_resources_path_is_used_everywhere(tmp_path: Path, gim_config: dict[str, Any]) -> None:
    """A configured resources_path replaces the default in every template and table."""
    config = MadcapHtmlOutputConfig(resources_path="../../../Shared/Resources/")

    MadcapHtmlOutput().generate(gim_config, tmp_path, config)

    refs = _stylesheet_refs(tmp_path)
    assert [r for r in refs if not r[1].startswith("../../../Shared/Resources/")] == []
    assert {r[1] for r in refs} >= {
        "../../../Shared/Resources/Stylesheets/Styles.css",
        "../../../Shared/Resources/TableStyles/Alternate-Row-Color.css",
    }


@pytest.mark.parametrize("value", ["../../Resources", "Resources", "../Shared Files/Resources_v2.1"])
def test_resources_path_accepts_safe_relative_paths(value: str) -> None:
    """Relative paths of letters, digits, '.', '_', '-' and spaces are accepted unchanged."""
    assert MadcapHtmlOutputConfig(resources_path=value).resources_path == value


def test_resources_path_trailing_slash_is_dropped() -> None:
    """A trailing slash is dropped, so links never contain '//'."""
    assert MadcapHtmlOutputConfig(resources_path="../Resources/").resources_path == "../Resources"


@pytest.mark.parametrize(
    "value",
    [
        "",
        "/Resources",
        "..\\Resources",
        "C:/Resources",
        "..//Resources",
        "../../R&D/Resources",
        "../../It's/Resources",
        '../../"Resources"',
        "../../<Resources>",
        "../../Re%20sources",
    ],
)
def test_resources_path_must_be_relative_with_safe_characters(value: str) -> None:
    """Empty, absolute, drive-letter, backslash and markup-breaking paths are rejected."""
    with pytest.raises(ValidationError):
        MadcapHtmlOutputConfig(resources_path=value)
