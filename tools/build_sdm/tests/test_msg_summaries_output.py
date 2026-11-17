import pytest
import json
import logging

from pathlib import Path
from pydantic import ValidationError

from output_plugins.message_summaries_output import (
    MessageSummariesOutput,
    MessageSummaryOutputConfig,
    DuplicateTemplateIDError,
    DuplicateIndicatorTemplateIDError
)


@pytest.fixture
def plugin():
    return MessageSummariesOutput()


def test_valid_summary_and_indicator_and_view(plugin):
    gim_category = {
        'name': 'testcat',
        'summaries': [
            {'template_id': 'tmpl1', 'summary': 's', 'title': 't', 'description': 'd'}
        ],
        'indicators': [
            {
                'default_indicator': 'info',
                'indicator': 'i',
                'type': 'type1',
                'title': 'ti',
                'description': 'desc',
                'success': ['ok'],
                'danger': ['fail'],
            }
        ],
        'subcategories': {
            'A': {
                'name': 'SubA',
                'summary': {
                    'title': 'sv1',
                    'description': 'd',
                    'summary_template': 'tmpl1',
                    'default_indicator': 'info'
                }
            }
        }
    }

    result = plugin.build_summary_dict(gim_category)
    assert 'summaries' in result
    assert len(result['summaries']['summaryTemplate']) == 1
    assert len(result['summaries']['indicatorTemplate']) == 1
    assert len(result['summaries']['summaryView']) == 1


def test_merges_with_existing_data(plugin):
    gim_category = {
        'name': 'testcat',
        'summaries': [
            {'template_id': 'tmpl2', 'summary': 's', 'title': 't', 'description': 'd'}
        ],
        'indicators': [],
        'subcategories': {}
    }

    existing = {
        'summaries': {
            'summaryTemplate': [{'template_id': 'tmpl1', 'summary': 's', 'title': 't', 'description': 'd'}],
            'indicatorTemplate': [],
            'summaryView': []
        }
    }

    result = plugin.build_summary_dict(gim_category, existing)
    template_ids = [t['template_id'] for t in result['summaries']['summaryTemplate']]
    assert 'tmpl1' in template_ids and 'tmpl2' in template_ids


def test_duplicate_summary_template_id_raises(plugin):
    gim_category = {
        'name': 'testcat',
        'summaries': [
            {'template_id': 'dup', 'summary': 's', 'title': 't', 'description': 'd'},
            {'template_id': 'dup', 'summary': 's2', 'title': 't2', 'description': 'd2'}
        ],
        'indicators': [],
        'subcategories': {}
    }

    with pytest.raises(DuplicateTemplateIDError):
        plugin.build_summary_dict(gim_category)


def test_duplicate_indicator_type_raises(plugin):
    gim_category = {
        'name': 'testcat',
        'summaries': [],
        'indicators': [
            {
                'default_indicator': 'info',
                'indicator': 'i',
                'type': 'dup',
                'title': 't1',
                'description': 'd',
                'success': ['ok'],
                'danger': ['bad'],
            },
            {
                'default_indicator': 'warning',
                'indicator': 'i2',
                'type': 'dup',
                'title': 't2',
                'description': 'd2',
                'success': ['ok2'],
                'danger': ['bad2'],
            }
        ],
        'subcategories': {}
    }

    with pytest.raises(DuplicateIndicatorTemplateIDError):
        plugin.build_summary_dict(gim_category)


def test_duplicate_summary_view_title_raises(plugin):
    gim_category = {
        'name': 'testcat',
        'summaries': [],
        'indicators': [],
        'subcategories': {
            'A': {
                'name': 'SubA',
                'summary': {
                    'title': 'dup',
                    'description': 'd',
                    'summary_template': 'tmpl',
                    'default_indicator': 'info'
                }
            },
            'B': {
                'name': 'SubB',
                'summary': {
                    'title': 'dup',
                    'description': 'd2',
                    'summary_template': 'tmpl',
                    'default_indicator': 'warning'
                }
            }
        }
    }

    with pytest.raises(DuplicateTemplateIDError):
        plugin.build_summary_dict(gim_category)


def test_invalid_summary_template_schema(plugin):
    gim_category = {
        'name': 'testcat',
        'summaries': [
            # Missing required "title" field
            {'template_id': 'tmpl1', 'summary': 's', 'description': 'd'}
        ],
        'indicators': [],
        'subcategories': {}
    }

    with pytest.raises(ValidationError):
        plugin.build_summary_dict(gim_category)


@pytest.fixture
def plugin():
    return MessageSummariesOutput()


@pytest.fixture
def valid_gim_config():
    return {
        'gim': {
            'testcat': {
                'name': 'testcat',
                'summaries': [
                    {'template_id': 'tmpl1', 'summary': 's', 'title': 't', 'description': 'd'}
                ],
                'indicators': [],
                'subcategories': {}
            }
        }
    }


def test_generate_writes_valid_json(plugin, tmp_path, valid_gim_config):
    plugin.generate(valid_gim_config, tmp_path)
    output_file = tmp_path / 'message_summaries.json'
    assert output_file.exists()
    data = json.loads(output_file.read_text())
    assert 'summaries' in data
    assert 'summaryTemplate' in data['summaries']


def test_generate_uses_default_config_when_none(plugin, tmp_path, valid_gim_config, caplog):
    caplog.set_level(logging.WARNING)
    plugin.generate(valid_gim_config, tmp_path, None)
    assert 'using default values' in caplog.text


def test_generate_respects_custom_config(plugin, tmp_path, valid_gim_config):
    cfg = MessageSummaryOutputConfig(output_filename='custom.json', json_indent=4)
    plugin.generate(valid_gim_config, tmp_path, cfg)
    output_file = tmp_path / 'custom.json'
    text = output_file.read_text()
    assert text.startswith('{\n    ')  # Pretty indent with 4 spaces


def test_generate_invalid_plugin_config_falls_back(plugin, tmp_path, valid_gim_config, caplog):
    caplog.set_level(logging.WARNING)
    plugin.generate(valid_gim_config, tmp_path, plugin_config={'bad': 'config'})
    assert 'using default values' in caplog.text


def test_generate_happy_path(tmp_path: Path):
    '''
    Ensure generate() produces a JSON file with summaries when given
    valid gim_config and plugin_config.
    '''
    plugin = MessageSummariesOutput()

    # Minimal valid gim_config with one summary template, indicator, and view
    gim_config = {
        'gim': {
            'network': {
                'name': 'network',
                'summaries': [
                    {
                        'template_id': 'net-1',
                        'summary': 'Network summary',
                        'title': 'Network Template',
                        'description': 'Some description',
                    }
                ],
                'indicators': [
                    {
                        'default_indicator': 'info',
                        'indicator': 'net-ind',
                        'type': 'net',
                        'title': 'Net Indicator',
                        'description': 'Desc',
                        'success': ['ok'],
                        'danger': ['fail'],
                    }
                ],
                'subcategories': {
                    '01': {
                        'name': 'firewall',
                        'summary': {
                            'title': 'Firewall View',
                            'description': 'FW desc',
                            'summary_template': 'net-1',
                            'default_indicator': 'info',
                        }
                    }
                }
            }
        }
    }

    plugin_config = MessageSummaryOutputConfig(
        output_filename='test_output.json',
        json_indent=2,
        enabled=True,
    )

    # Run the plugin
    plugin.generate(gim_config, tmp_path, plugin_config)

    # Verify file was created
    output_file = tmp_path / 'test_output.json'
    assert output_file.exists()

    # Verify contents are valid JSON and contain expected structures
    with output_file.open('r', encoding='utf-8') as f:
        data = json.load(f)

    assert 'summaries' in data
    assert 'summaryTemplate' in data['summaries']
    assert 'indicatorTemplate' in data['summaries']
    assert 'summaryView' in data['summaries']

    # Check that IDs match what we provided
    templates = data['summaries']['summaryTemplate']
    assert any(t['template_id'] == 'net-1' for t in templates)

    indicators = data['summaries']['indicatorTemplate']
    assert any(i['type'] == 'net' for i in indicators)

    views = data['summaries']['summaryView']
    assert any(v['title'] == 'Firewall View' for v in views)


def test_generate_with_duplicate_summary_template(tmp_path: Path):
    '''
    Ensure generate() raises DuplicateTemplateIDError when gim_config
    contains duplicate summary template IDs.
    '''
    plugin = MessageSummariesOutput()

    gim_config = {
        'gim': {
            'network': {
                'name': 'network',
                'summaries': [
                    {
                        'template_id': 'dup-1',
                        'summary': 'First summary',
                        'title': 'Template One',
                        'description': 'desc',
                    },
                    {
                        'template_id': 'dup-1',  # duplicate
                        'summary': 'Second summary',
                        'title': 'Template Two',
                        'description': 'desc',
                    }
                ],
                'indicators': [],
                'subcategories': {},
            }
        }
    }

    plugin_config = MessageSummaryOutputConfig(output_filename='out.json')

    with pytest.raises(DuplicateTemplateIDError):
        plugin.generate(gim_config, tmp_path, plugin_config)


def test_generate_file_write_failure(tmp_path: Path, caplog):
    '''
    Ensure generate() logs an error if it fails to write the JSON file.
    '''
    plugin = MessageSummariesOutput()
    plugin_config = MessageSummaryOutputConfig(output_filename='out.json')

    # Create a file with the same name as the intended output directory
    bad_output_dir = tmp_path / 'not_a_dir'
    bad_output_dir.write_text('I am a file, not a directory')

    gim_config = {
        'gim': {
            'system': {
                'name': 'system',
                'summaries': [
                    {
                        'template_id': 'sys-1',
                        'summary': 'System summary',
                        'title': 'System Template',
                        'description': 'desc',
                    }
                ],
                'indicators': [],
                'subcategories': {},
            }
        }
    }

    caplog.set_level(logging.ERROR, logger=plugin.logger.name)

    plugin.generate(gim_config, bad_output_dir, plugin_config)

    errors = [rec for rec in caplog.records if rec.levelname == 'ERROR']
    assert any('Unable to write' in rec.getMessage() for rec in errors)
