import logging

from unittest.mock import patch, MagicMock
from build_sdm.output_plugins.madcap_html_output import MadcapHtmlOutput, MadcapHtmlOutputConfig

def test_generate_invokes_internal_methods(tmp_path):
    '''
    Unit test for MadcapHtmlOutput.generate() that ensures internal methods are called
    correctly and output files are attempted.
    '''
    plugin = MadcapHtmlOutput()
    plugin.logger.setLevel(logging.CRITICAL)
    output_dir = tmp_path
    mock_gim_config = {
        'config': {},
        'gim': {
            'network': {
                'meta': {
                    'plugin_config': {
                        'MadcapHtmlOutput': {
                            'category_template_filename': 'mock_template.j2'
                        }
                    }
                }
            }
        }
    }

    plugin_config = MadcapHtmlOutputConfig(enabled=True)

    with (
        patch.object(plugin, '_resolve_plugin_config', return_value=plugin_config) as mock_resolve,
        patch.object(plugin, '_initialize_jinja_environment') as mock_init_env,
        patch.object(plugin, '_validate_category_plugin_config') as mock_validate,
        patch.object(plugin, '_load_template') as mock_load_template,
        patch.object(plugin, '_render_template') as mock_render,
    ):
        mock_validate.return_value = MagicMock(category_template_filename='mock_template.j2')
        mock_load_template.return_value = MagicMock()
        mock_render.return_value = '<html>Rendered</html>'

        plugin.generate(mock_gim_config, output_dir, plugin_config)

        mock_resolve.assert_called_once_with(plugin_config)
        mock_init_env.assert_called_once_with()
        mock_validate.assert_called_once()
        mock_load_template.assert_called_once_with('mock_template.j2', 'network')
        mock_render.assert_called_once()
