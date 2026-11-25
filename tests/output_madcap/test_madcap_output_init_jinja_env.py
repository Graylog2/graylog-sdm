import logging
from pathlib import Path
from build_sdm.output_plugins.madcap_html_output import MadcapHtmlOutput
from build_sdm.output_plugins.madcap_html_output.models import DEFAULT_RESOURCES_PATH


def test_initialize_jinja_environment_creates_env(tmp_path, caplog):
    '''Test that the Jinja env is initialized correctly and log is emitted'''
    plugin = MadcapHtmlOutput()
    plugin.logger.setLevel(logging.DEBUG)
    caplog.set_level(logging.DEBUG)

    expected_path = tmp_path / 'html_templates'
    expected_path.mkdir(parents=True)

    plugin._initialize_jinja_environment(template_dir=expected_path)

    assert plugin._env is not None, 'Expected _env to be initialized'
    assert str(plugin._env.loader.searchpath[0]) == str(expected_path)
    assert f'Using template directory [{expected_path}]' in caplog.text


def test_initialize_jinja_environment_missing_directory(caplog, tmp_path):
    '''Test for failed initialization of the Jinja env due to a missing dir to verify plugin does not crash and log is emitted'''
    plugin = MadcapHtmlOutput()
    plugin.logger.setLevel(logging.DEBUG)
    caplog.set_level(logging.DEBUG)

    # Do not create the directory
    expected_path = tmp_path / 'nonexistent_html_templates'

    plugin._initialize_jinja_environment(template_dir=expected_path)

    # It still initializes, but the directory doesn't exist
    assert plugin._env is not None
    assert str(plugin._env.loader.searchpath[0]) == str(expected_path)
    assert f'Using template directory [{expected_path}]' in caplog.text


def test_initialize_jinja_environment_sets_resources_path_global(tmp_path):
    '''Templates and macros read resources_path as a global: the default, or the value passed in'''
    plugin = MadcapHtmlOutput()

    plugin._initialize_jinja_environment(template_dir=tmp_path)
    assert plugin._env.globals['resources_path'] == DEFAULT_RESOURCES_PATH

    plugin._initialize_jinja_environment(template_dir=tmp_path, resources_path='../Res')
    assert plugin._env.globals['resources_path'] == '../Res'
