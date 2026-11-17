import logging
from output_plugins.madcap_html_output import MadcapHtmlOutput, MadcapHtmlOutputConfig

def test_resolve_plugin_config_valid(caplog):
    plugin = MadcapHtmlOutput()
    plugin.logger.setLevel(logging.DEBUG)
    caplog.set_level(logging.DEBUG)

    valid_config = MadcapHtmlOutputConfig(enabled=True)
    resolved = plugin._resolve_plugin_config(valid_config)

    assert isinstance(resolved, MadcapHtmlOutputConfig)
    assert resolved.enabled is True
    assert 'Validated top-level plugin config provided' in caplog.text


def test_resolve_plugin_config_none(caplog):
    plugin = MadcapHtmlOutput()
    plugin.logger.setLevel(logging.WARNING)
    caplog.set_level(logging.WARNING)

    resolved = plugin._resolve_plugin_config(None)

    assert isinstance(resolved, MadcapHtmlOutputConfig)
    assert resolved.enabled is False
    assert 'Plugin config missing or invalid; using defaults.' in caplog.text
