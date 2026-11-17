import importlib
import pkgutil

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

import output_plugins
from runner import _load_and_transform_gim_config


def _ensure_plugins_imported():
    '''Import every output_plugins submodule so plugin_name lookups resolve.'''
    for _, name, _ in pkgutil.walk_packages(output_plugins.__path__, output_plugins.__name__ + '.'):
        importlib.import_module(name)

# Mocks
def fake_loader_success(path, merge):
    return {
        'file1.toml': {
            'type': 'gim',
            'network': {'meta': {}}
        },
        'settings': {'gim_dir': str(path)}
    }

def fake_transform_success(input_data):
    return {'gim': input_data.get('file1.toml', {}), 'settings': input_data['settings']}

def test_load_and_transform_gim_config_success(monkeypatch):
    '''
    Validates _load_and_transform_gim_config loads and restructures a real directory.
    '''
    with TemporaryDirectory() as tmp_dir_name:
        tmp_dir_path = Path(tmp_dir_name)
        gim_path = tmp_dir_path / '_meta' / 'gim'
        gim_path.mkdir(parents=True)

        monkeypatch.setattr('runner.load_gim_config_files', fake_loader_success)
        monkeypatch.setattr('runner.restructure_gim_config', fake_transform_success)

        script_config = {'global': {'gim_source_dir': '_meta/gim'}}

        result = _load_and_transform_gim_config(tmp_dir_path, script_config)

        assert 'gim' in result
        assert 'settings' in result
        assert result['settings']['gim_dir'].endswith('_meta/gim')

def test_load_and_transform_gim_config_dir_missing():
    '''
    Should raise NotADirectoryError when gim_dir does not exist.
    '''
    script_config = {'global': {'gim_source_dir': '_meta/gim'}}
    repo_dir = Path('/nonexistent/directory/path')

    with pytest.raises(NotADirectoryError):
        _load_and_transform_gim_config(repo_dir, script_config)

def test_load_and_transform_gim_config_loader_failure(monkeypatch, tmp_path):
    '''
    Should raise exception and log fatal if loader fails during GIM load.
    '''
    def fake_loader_fail(*args, **kwargs):
        raise RuntimeError('Simulated loader failure')

    gim_path = tmp_path / '_meta' / 'gim'
    gim_path.mkdir(parents=True)

    monkeypatch.setattr('runner.load_gim_config_files', fake_loader_fail)

    script_config = {'global': {'gim_source_dir': '_meta/gim'}}

    with pytest.raises(RuntimeError, match='Simulated loader failure'):
        _load_and_transform_gim_config(tmp_path, script_config)

def test_load_and_transform_gim_config_rejects_dangling_applies_to(monkeypatch, tmp_path):
    '''
    Should raise ValueError when restructured field_schema data has a sub-entity
    applies_to referencing an entity that isn't a known "top" entity.
    '''
    gim_path = tmp_path / '_meta' / 'gim'
    gim_path.mkdir(parents=True)

    def fake_loader(path, merge):
        return {}

    def fake_transform(input_data):
        return {
            'field_schema': {
                'hash': {
                    'entity_type': 'sub',
                    'applies_to': ['does_not_exist'],
                    'fields': []
                }
            }
        }

    monkeypatch.setattr('runner.load_gim_config_files', fake_loader)
    monkeypatch.setattr('runner.restructure_gim_config', fake_transform)

    script_config = {'global': {'gim_source_dir': '_meta/gim'}}

    with pytest.raises(ValueError, match='does_not_exist'):
        _load_and_transform_gim_config(tmp_path, script_config)

def test_load_and_transform_real_gim_config_passes_applies_to_validation():
    '''
    Loads the actual repo _meta/gim directory end-to-end, confirming the real
    field_schema data (including sub-entities like hash, geo, and as) satisfies
    applies_to validation.
    '''
    _ensure_plugins_imported()
    repo_dir = Path(__file__).resolve().parents[3]
    script_config = {'global': {'gim_source_dir': '_meta/gim'}}

    result = _load_and_transform_gim_config(repo_dir, script_config)

    assert 'field_schema' in result
