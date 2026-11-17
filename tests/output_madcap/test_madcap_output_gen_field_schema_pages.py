import pytest

from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock
from copy import deepcopy

from build_sdm.output_plugins.madcap_html_output import MadcapHtmlOutput
from build_sdm.output_plugins.madcap_html_output.models import MadcapHtmlOutputConfig


# ----------------------------------------------------------------------
# FIXTURES
# ----------------------------------------------------------------------

@pytest.fixture
def mock_plugin() -> MadcapHtmlOutput:
    '''
    Fixture that returns a mocked MadcapHtmlOutput instance with stubbed dependencies.
    Ensures all attributes used by _generate_field_schema_entity_pages() return
    expected types, while letting real validation/composition logic run.
    '''
    plugin = MadcapHtmlOutput()
    plugin.plugin_name = 'build_sdm.output_plugins.madcap_html_output.plugin.MadcapHtmlOutput'
    plugin.logger = MagicMock()

    mock_template = MagicMock()
    plugin._load_template = MagicMock(return_value=mock_template)
    plugin._render_template = MagicMock(return_value='<html>Rendered</html>')

    return plugin


@pytest.fixture
def gim_config() -> Callable[[], dict[str, Any]]:
    '''
    Fixture factory returning a minimal field_schema config with a "top" entity
    (file) and a "sub" entity (hash) attached to it via applies_to.
    '''
    base_cfg = {
        'field_schema': {
            'file': {
                'entity_type': 'top',
                'description': 'File fields',
                'fields': [
                    {
                        'field_suffix': 'name',
                        'field_type': 'keyword',
                        'description': 'File name',
                        'example_values': ''
                    }
                ]
            },
            'hash': {
                'entity_type': 'sub',
                'description': 'Hash sub-fields',
                'applies_to': ['file'],
                'fields': [
                    {
                        'field_suffix': 'md5',
                        'field_type': 'keyword',
                        'description': 'MD5 hash value',
                        'example_values': ''
                    }
                ]
            }
        },
        'config': {}
    }

    def _factory() -> dict:
        return deepcopy(base_cfg)

    return _factory


def _rendered_schema_data_by_entity(mock_plugin: MadcapHtmlOutput) -> dict:
    '''Map entity_name to the schema_data dict passed to each _render_template call.'''
    return {
        call.args[1]: call.args[2]
        for call in mock_plugin._render_template.call_args_list
    }


# ----------------------------------------------------------------------
# TESTS
# ----------------------------------------------------------------------

def test_parent_entity_page_groups_composed_subfield_rows_by_source(
    mock_plugin: MadcapHtmlOutput,
    gim_config: Callable[[], dict[str, Any]],
    tmp_path: Path
) -> None:
    '''
    Should compose the sub-entity's fields onto the parent entity's schema_data
    as subfield_groups, one group per source sub-entity, using the
    {parent}_{sub_entity}_{suffix} field name within each group.
    '''
    cfg = gim_config()

    mock_plugin._generate_field_schema_entity_pages(cfg, tmp_path, MadcapHtmlOutputConfig())

    schema_data_by_entity = _rendered_schema_data_by_entity(mock_plugin)
    subfield_groups = schema_data_by_entity['file']['subfield_groups']

    assert len(subfield_groups) == 1
    assert subfield_groups[0]['source_entity'] == 'hash'
    assert [row['field'] for row in subfield_groups[0]['rows']] == ['file_hash_md5']


def test_parent_entity_page_creates_one_group_per_sub_entity(
    mock_plugin: MadcapHtmlOutput,
    gim_config: Callable[[], dict[str, Any]],
    tmp_path: Path
) -> None:
    '''
    Should create a separate subfield_groups entry, sorted by source_entity,
    for each sub-entity attached to the same parent.
    '''
    cfg = gim_config()
    cfg['field_schema']['geo'] = {
        'entity_type': 'sub',
        'description': 'Geo sub-fields',
        'applies_to': ['file'],
        'fields': [
            {
                'field_suffix': 'city',
                'field_type': 'keyword',
                'description': 'City',
                'example_values': ''
            }
        ]
    }

    mock_plugin._generate_field_schema_entity_pages(cfg, tmp_path, MadcapHtmlOutputConfig())

    schema_data_by_entity = _rendered_schema_data_by_entity(mock_plugin)
    subfield_groups = schema_data_by_entity['file']['subfield_groups']

    assert [group['source_entity'] for group in subfield_groups] == ['geo', 'hash']


def test_sub_entity_page_has_no_subfield_groups_and_carries_applies_to(
    mock_plugin: MadcapHtmlOutput,
    gim_config: Callable[[], dict[str, Any]],
    tmp_path: Path
) -> None:
    '''
    Should leave subfield_groups empty on a sub-entity's own page, while
    passing its applies_to list through unchanged.
    '''
    cfg = gim_config()

    mock_plugin._generate_field_schema_entity_pages(cfg, tmp_path, MadcapHtmlOutputConfig())

    schema_data_by_entity = _rendered_schema_data_by_entity(mock_plugin)
    hash_schema_data = schema_data_by_entity['hash']

    assert hash_schema_data['subfield_groups'] == []
    assert hash_schema_data['applies_to'] == ['file']


def test_rendered_html_links_parent_and_subfield_pages(
    gim_config: Callable[[], dict[str, Any]],
    tmp_path: Path
) -> None:
    '''
    End-to-end render (real Jinja templates, no mocking): the parent entity's page
    should show the composed sub-field name and link to the sub-entity's page, and
    the sub-entity's page should show an "Applies to" link back to the parent.
    '''
    plugin = MadcapHtmlOutput()
    plugin.plugin_name = 'build_sdm.output_plugins.madcap_html_output.plugin.MadcapHtmlOutput'
    plugin.logger = MagicMock()
    plugin._initialize_jinja_environment()

    cfg = gim_config()

    plugin._generate_field_schema_entity_pages(cfg, tmp_path, MadcapHtmlOutputConfig())

    file_html = (tmp_path / 'field_schema' / 'file.html').read_text(encoding='utf-8')
    hash_html = (tmp_path / 'field_schema' / 'hash.html').read_text(encoding='utf-8')

    assert 'file_hash_md5' in file_html
    assert 'href="hash.html"' in file_html
    assert 'href="file.html"' in hash_html
    assert '<MadCap:dropDown>' in file_html


def test_entity_with_no_attached_subfields_gets_empty_subfield_groups(
    mock_plugin: MadcapHtmlOutput,
    gim_config: Callable[[], dict[str, Any]],
    tmp_path: Path
) -> None:
    '''
    Should leave subfield_groups empty for a top entity with no sub-fields
    attached to it.
    '''
    cfg = gim_config()
    cfg['field_schema']['process'] = {
        'entity_type': 'top',
        'description': 'Process fields',
        'fields': []
    }

    mock_plugin._generate_field_schema_entity_pages(cfg, tmp_path, MadcapHtmlOutputConfig())

    schema_data_by_entity = _rendered_schema_data_by_entity(mock_plugin)
    assert schema_data_by_entity['process']['subfield_groups'] == []
