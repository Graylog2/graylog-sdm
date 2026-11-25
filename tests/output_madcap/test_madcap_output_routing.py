import logging
from pathlib import Path
from unittest.mock import patch
from build_sdm.output_plugins.madcap_html_output import MadcapHtmlOutput, MadcapHtmlOutputConfig

def test_plugin_output_subdir_routing(tmp_path: Path):
    '''
    Verify that plugin respects html_output_subdir for each section,
    and falls back to sanitized section name when not set.
    '''
    plugin = MadcapHtmlOutput()
    plugin.logger.setLevel(logging.CRITICAL)

    # Setup template
    template_name = 'simple_template.j2'
    template_content = '<html><body>{{ category }}</body></html>'
    template_dir = tmp_path / 'html_templates'
    template_dir.mkdir()
    (template_dir / template_name).write_text(template_content, encoding='utf-8')

    plugin_config = MadcapHtmlOutputConfig()

    gim_config = {
        'config': {},
        'config_output_plugin': {
            'plugin': {
                'build_sdm.output_plugins.madcap_html_output.plugin.MadcapHtmlOutput': {
                    'gim': {
                        'template': template_name,
                        'output_filename': 'GIM_Output.html',
                        'html_output_subdir': 'gim_docs'
                    },
                    'field_schema': {
                        'template': template_name,
                        'output_filename': 'FieldSchema_Output.html'
                        # No html_output_subdir specified here
                    }
                }
            }
        },
        'gim': {},  # No category data needed for top-level page
        'field_schema': {}  # No category data needed for top-level page
    }

    with patch.object(plugin, '_initialize_jinja_environment',
                      side_effect=lambda **kwargs: MadcapHtmlOutput._initialize_jinja_environment(
                          plugin, template_dir=template_dir, **kwargs
                      )):
        plugin.generate(gim_config, tmp_path, plugin_config)

    expected_gim_path = tmp_path / 'gim_docs' / 'GIM_Output.html'
    expected_field_schema_path = tmp_path / 'field_schema' / 'FieldSchema_Output.html'

    assert expected_gim_path.exists(), 'GIM top-level output file was not created.'
    assert expected_field_schema_path.exists(), 'Field schema top-level output file was not created.'

    with expected_gim_path.open(encoding='utf-8') as f:
        assert 'gim' in f.read()

    with expected_field_schema_path.open(encoding='utf-8') as f:
        assert 'field_schema' in f.read()
