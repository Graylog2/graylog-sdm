import logging

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from output_plugins.madcap_html_output import MadcapHtmlOutput, MadcapHtmlOutputConfig


def test_generate_real_world(tmp_path: Path):
    '''
    End-to-end test of the generate() method with a minimal valid GIM config and template.
    '''
    plugin = MadcapHtmlOutput()
    plugin.logger.setLevel(logging.CRITICAL)

    # Create temporary template file
    template_file_name = 'gim_category_template.j2'
    template_content = '<html><body><h1>{{ category }}</h1></body></html>'

    template_dir_path = tmp_path / 'html_templates'
    template_dir_path.mkdir()
    (template_dir_path / template_file_name).write_text(template_content, encoding='utf-8')

    # Define GIM config input
    gim_config = {
        'config': {},
        'gim': {
            'network': {
                'meta': {
                    'plugin_config': {
                        'MadcapHtmlOutput': {
                            'category_template_filename': template_file_name
                        }
                    }
                }
            }
        }
    }

    # Run plugin generate method, injecting the temporary template directory
    plugin_config = MadcapHtmlOutputConfig()
    with patch.object(plugin, '_initialize_jinja_environment',
                      side_effect=lambda: MadcapHtmlOutput._initialize_jinja_environment(
                          plugin, template_dir=template_dir_path
                      )):
        plugin.generate(gim_config, tmp_path, plugin_config)

    # Verify expected HTML output
    expected_file = tmp_path / 'gim' / 'network.html'
    assert expected_file.exists(), 'Expected HTML file was not created.'

    content = expected_file.read_text(encoding='utf-8')
    assert '<h1>network</h1>' in content, 'Rendered HTML content does not match expected output.'


def test_generate_template_not_found(caplog):
    '''
    Simulate a generate() run where the template file is missing.
    Ensures graceful failure and no output written.
    '''
    plugin = MadcapHtmlOutput()
    plugin.logger.setLevel(logging.ERROR)
    caplog.set_level(logging.ERROR)

    with TemporaryDirectory() as tmp_dir_name:
        output_dir = Path(tmp_dir_name)
        template_dir = output_dir / 'html_templates'
        template_dir.mkdir()

        gim_config = {
            'config': {},
            'gim': {
                'network': {
                    'meta': {
                        'plugin_config': {
                            'output_plugins.madcap_html_output.plugin.MadcapHtmlOutput': {
                                'category_template_filename': 'missing_template.j2'
                            }
                        }
                    }
                }
            }
        }

        plugin_config = MadcapHtmlOutputConfig(enabled=True)
        with patch.object(plugin, '_initialize_jinja_environment',
                          side_effect=lambda: MadcapHtmlOutput._initialize_jinja_environment(
                              plugin, template_dir=template_dir
                          )):
            plugin.generate(gim_config=gim_config, output_dir=output_dir, plugin_config=plugin_config)

        expected_error = f'Template not found [missing_template.j2] for category [network]'

        # Assert error was logged about template failure
        assert any(
            expected_error in message for message in caplog.messages
        ), 'Expected template load failure to be logged'

        # Assert no output file was created
        output_file = output_dir / 'network.html'
        assert not output_file.exists(), 'No HTML output should be written on template failure'


def test_generate_missing_plugin_config_uses_defaults(tmp_path: Path):
    '''
    Ensure that if plugin_config is missing from the GIM category, the plugin uses default values.
    '''
    plugin = MadcapHtmlOutput()
    plugin.logger.setLevel(logging.CRITICAL)

    # Create default template file that would be used by default config
    default_template_name = 'gim_category_template.j2'
    template_content = '<html><body><h1>{{ category }}</h1></body></html>'
    template_dir = tmp_path / 'html_templates'
    template_dir.mkdir()
    (template_dir / default_template_name).write_text(template_content, encoding='utf-8')

    gim_config = {
        'config': {},
        'gim': {
            'network': {
                'meta': {
                    # plugin_config intentionally omitted
                }
            }
        }
    }

    plugin_config = MadcapHtmlOutputConfig()
    with patch.object(plugin, '_initialize_jinja_environment',
                      side_effect=lambda: MadcapHtmlOutput._initialize_jinja_environment(
                          plugin, template_dir=template_dir
                      )):
        plugin.generate(gim_config=gim_config, output_dir=tmp_path, plugin_config=plugin_config)

    output_file = tmp_path / 'gim' / 'network.html'
    assert output_file.exists(), 'Expected output file was not generated using default config.'

    content = output_file.read_text(encoding='utf-8')
    assert '<h1>network</h1>' in content, 'Rendered content did not match expected default template output.'
