import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from output_plugins.sample_plaintext_output import (
    PlainTextOutput,
    PlainTextOutputConfig
)

class DummyConfig:
    field: str = 'default'

def test_plugin_instantiation():
    '''
    The plugin should instantiate without errors and set up its logger.
    '''
    plugin = PlainTextOutput()
    assert isinstance(plugin, PlainTextOutput)
    assert hasattr(plugin, 'logger')


def test_plugin_generate_with_valid_config(tmp_path: Path):
    '''
    Run generate() with a valid plugin config and confirm file creation and content.
    '''
    plugin = PlainTextOutput()
    plugin.logger.setLevel(logging.CRITICAL)

    # Prepare GIM config
    gim_config = {
        'gim': {'network': {'description': 'Test category'}},
        'config': {'example': True}
    }

    # Provide a custom output filename via config
    plugin_config = PlainTextOutputConfig(output_filename='custom_output.txt', enabled=True)

    plugin.generate(gim_config, tmp_path, plugin_config)

    expected_file = tmp_path / 'custom_output.txt'
    assert expected_file.exists(), 'Expected output file was not created'

    content = expected_file.read_text(encoding='utf-8')
    assert '=== GIM CONFIG DUMP ===' in content
    assert 'gim' in content
    assert 'config' in content


def test_plugin_generate_without_config(tmp_path: Path):
    '''
    Run generate() without a config and confirm fallback to default config.
    '''
    plugin = PlainTextOutput()
    plugin.logger.setLevel(logging.CRITICAL)

    gim_config = {'gim': {}, 'config': {}}

    plugin.generate(gim_config, tmp_path)

    default_file = tmp_path / 'output.txt'
    assert default_file.exists()
    assert '=== GIM CONFIG DUMP ===' in default_file.read_text(encoding='utf-8')


def test_plugin_generate_write_error(monkeypatch):
    '''
    Simulate a file write failure and confirm the plugin handles the error.
    '''
    plugin = PlainTextOutput()
    plugin.logger.setLevel(logging.CRITICAL)

    gim_config = {'gim': {}, 'config': {}}
    plugin_config = PlainTextOutputConfig(output_filename='output.txt')

    class MockPath:
        def __truediv__(self, other):
            return self

        def open(self, mode, encoding=None):
            raise IOError('Simulated write failure')

    with TemporaryDirectory() as tmp_dir:
        output_dir = MockPath()
        plugin.generate(gim_config, output_dir, plugin_config)
        # No assertion necessary — test will fail if an exception propagates

