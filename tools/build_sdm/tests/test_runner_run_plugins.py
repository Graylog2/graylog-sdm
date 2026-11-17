import logging
from pathlib import Path
from runner import _run_plugins

class DummyPlugin:
    def __init__(self):
        self.generated = False
        self.logger = logging.getLogger('plugin.DummyPlugin')
        self.logger.setLevel(logging.INFO)
        self.logged_messages = []

        # Capture log messages for dry-run test
        self.logger.addHandler(self._make_log_handler())

    def generate(self, gim_config, output_dir, plugin_config=None):
        self.generated = True

    def _make_log_handler(self):
        class CaptureHandler(logging.Handler):
            def __init__(self, parent):
                super().__init__()
                self.parent = parent

            def emit(self, record):
                self.parent.logged_messages.append(record.getMessage())

        return CaptureHandler(self)

def test_run_plugins_normal(monkeypatch):
    '''
    Should invoke the generate method of a plugin when dry_run is False.
    '''
    plugin = DummyPlugin()
    plugins = [(plugin, {})]

    monkeypatch.setattr('runner.load_plugins_with_config', lambda *_args, **_kwargs: plugins)

    _run_plugins(
        script_config={'plugins': {}},
        gim_config={'gim': {}},
        output_dir=Path('/tmp'),
        dry_run=False
    )

    assert plugin.generated is True

def test_run_plugins_dry_run(monkeypatch):
    '''
    Should NOT call generate, and instead log a dry-run message.
    '''
    plugin = DummyPlugin()
    plugins = [(plugin, {})]

    monkeypatch.setattr('runner.load_plugins_with_config', lambda *_args, **_kwargs: plugins)

    _run_plugins(
        script_config={'plugins': {}},
        gim_config={'gim': {}},
        output_dir=Path('/tmp'),
        dry_run=True
    )

    assert plugin.generated is False
    assert any('Would generate output using plugin' in msg for msg in plugin.logged_messages)
