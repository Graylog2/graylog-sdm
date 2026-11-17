import pytest
from build_sdm.runner import _load_script_config
from pathlib import Path
from unittest.mock import patch

def test_load_script_config_valid(monkeypatch):
    '''
    Should return the loaded config if it contains 'global' and 'plugins'.
    '''
    fake_config = {
        'global': {'output_dir': '/tmp'},
        'plugins': {'SomePlugin': {}}
    }

    monkeypatch.setattr('build_sdm.runner.load_script_config_files', lambda _p: fake_config)

    config = _load_script_config(Path('/some/config/dir'))
    assert config == fake_config

def test_load_script_config_invalid(monkeypatch):
    '''
    Should raise RuntimeError if config is missing required keys.
    '''
    # Simulate a config missing 'plugins' section
    incomplete_config = {'global': {'output_dir': '/tmp'}}

    monkeypatch.setattr('build_sdm.runner.load_script_config_files', lambda _p: incomplete_config)

    with pytest.raises(RuntimeError, match='Invalid or missing script config'):
        _load_script_config(Path('/fake/path'))
