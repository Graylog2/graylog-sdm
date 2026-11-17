"""Render tests for the top-level page section macro (macros/top_level_page_sections.j2)."""

import pytest
from jinja2 import Environment

from build_sdm.output_plugins.madcap_html_output import MadcapHtmlOutput


@pytest.fixture
def env() -> Environment:
    """Return the plugin's Jinja environment over the packaged templates."""
    plugin = MadcapHtmlOutput()
    plugin._initialize_jinja_environment()
    assert plugin._env is not None
    return plugin._env


def _render_section(env: Environment, section: dict[str, str]) -> str:
    """Render one section through the render_section macro.

    Args:
        env: Jinja environment with the packaged templates.
        section: Section definition as validated by SectionDefinition.

    Returns:
        The rendered HTML.
    """
    template = env.from_string(
        '{% import "macros/top_level_page_sections.j2" as s %}{{ s.render_section(section) }}'
    )
    return template.render(section=section)


@pytest.mark.parametrize(
    ("section_type", "box_class", "label"),
    [
        ("hint", "infoBox", "Hint: "),
        ("warning", "warningBox", "Warning: "),
    ],
)
def test_single_line_box_renders_whole_text(
    env: Environment, section_type: str, box_class: str, label: str
) -> None:
    """A one-line hint or warning renders as one block containing the full text."""
    html = _render_section(env, {"type": section_type, "content": "Use TLS"})

    assert f'class="{box_class}"' in html
    assert f'<b>{label}</b><span style="font-weight: normal;">Use TLS</span>' in html
    assert html.count('<div class="content">') == 1


@pytest.mark.parametrize(("section_type", "label"), [("hint", "Hint: "), ("warning", "Warning: ")])
def test_multi_line_box_renders_one_block_per_line(env: Environment, section_type: str, label: str) -> None:
    """Each non-blank line of a hint or warning renders as its own block."""
    html = _render_section(env, {"type": section_type, "content": "First line\n\nSecond line"})

    assert f'<b>{label}</b><span style="font-weight: normal;">First line</span>' in html
    assert '<span style="font-weight: normal;">Second line</span>' in html
    assert html.count('<div class="content">') == 2
