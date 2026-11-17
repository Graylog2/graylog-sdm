from output_plugins.madcap_html_output import MadcapHtmlOutput, MadcapTopLevelConfig

def test_load_top_level_config_valid():
    plugin = MadcapHtmlOutput()
    raw_plugin_config = {
        'gim': {
            'title': 'Top Title',
            'intro': 'Intro text'
        },
        'field_schema': {
            'title': 'Field Title',
            'intro': 'Field intro',
            'template': 'custom_field_template.j2'
        }
    }

    config = plugin.load_top_level_config(raw_plugin_config)
    assert isinstance(config, MadcapTopLevelConfig)
    assert config.gim['title'] == 'Top Title'
    assert config.field_schema['template'] == 'custom_field_template.j2'