import pytest
from build_sdm.runner import _load_script_config

def test_load_script_config_valid(monkeypatch):
    '''
    Should return script config when required keys are present.
    '''
    dummy_config = {
        'global': {'output_dir': 'out'},
        'plugins': [{'name': 'ExamplePlugin'}]
    }

    monkeypatch.setattr('build_sdm.runner.load_script_config_files', lambda _: dummy_config)
    result = _load_script_config('some/path')
    assert result == dummy_config


def test_load_script_config_missing_keys(monkeypatch):
    '''
    Should raise RuntimeError when required keys are missing.
    '''
    monkeypatch.setattr('build_sdm.runner.load_script_config_files', lambda _: {'global': {}})
    with pytest.raises(RuntimeError):
        _ = _load_script_config('some/path')

def test_load_script_config_logs(monkeypatch, caplog):
    '''
    Should log the attempt to load script config.
    '''
    dummy_config = {
        'global': {'output_dir': 'out'},
        'plugins': [{'name': 'ExamplePlugin'}]
    }

    monkeypatch.setattr('build_sdm.runner.load_script_config_files', lambda _: dummy_config)

    with caplog.at_level('DEBUG'):
        _ = _load_script_config('some/path')

    assert any('Attempting to load script config' in msg for msg in caplog.messages)
