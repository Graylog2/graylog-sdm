import output_plugins
import pytest
from unittest.mock import patch, MagicMock
from runner import _scan_and_import_plugins


def test_scan_and_import_plugins():
    '''
    Should call importlib.import_module for each discovered plugin module.
    '''
    # Simulate one fake plugin module found by pkgutil
    fake_plugin_name = 'output_plugins.fake_plugin'
    fake_module_info = (None, fake_plugin_name, False)

    with patch('runner.pkgutil.walk_packages', return_value=[fake_module_info]) as mock_walk, \
         patch('runner.importlib.import_module') as mock_import:

        _scan_and_import_plugins()

        # Validate walk_packages was called correctly
        mock_walk.assert_called_once_with(
            output_plugins.__path__,
            output_plugins.__name__ + '.'
        )

        # Validate importlib.import_module was called with the plugin name
        mock_import.assert_called_once_with(fake_plugin_name)

def test_scan_and_import_plugins_multiple():
    '''
    Should import multiple discovered plugin modules.
    '''
    plugin_names = [
        'output_plugins.plugin_a',
        'output_plugins.plugin_b',
        'output_plugins.plugin_c'
    ]
    fake_plugins = [(None, name, False) for name in plugin_names]

    with patch('runner.pkgutil.walk_packages', return_value=fake_plugins) as mock_walk, \
         patch('runner.importlib.import_module') as mock_import:

        _scan_and_import_plugins()

        # Validate walk_packages was called correctly
        mock_walk.assert_called_once_with(
            output_plugins.__path__,
            output_plugins.__name__ + '.'
        )

        # Validate each discovered plugin was imported
        import_calls = [((name,),) for name in plugin_names]
        mock_import.assert_has_calls(import_calls, any_order=False)
        assert mock_import.call_count == len(plugin_names)

def test_scan_and_import_plugins_empty(monkeypatch):
    '''
    Should do nothing if no plugins are discovered.
    '''
    monkeypatch.setattr('runner.pkgutil.walk_packages', lambda *_: [])
    monkeypatch.setattr('runner.importlib.import_module', pytest.fail)  # Should never be called

    _scan_and_import_plugins()