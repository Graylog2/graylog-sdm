import pytest
from pathlib import Path
from runner import run_build

def test_run_build_success(monkeypatch):
    '''
    Should call all sub-steps successfully when everything works as expected.
    '''
    called = {}

    monkeypatch.setattr('runner._scan_and_import_plugins', lambda: called.setdefault('scan', True))

    dummy_script_config = {
        'global': {'output_dir': 'out', 'gim_source_dir': '_meta/gim'},
        'plugins': [{'name': 'ExamplePlugin'}]
    }
    monkeypatch.setattr('runner._load_script_config', lambda path: called.setdefault('load_config', dummy_script_config))
    monkeypatch.setattr('runner._ensure_output_dir', lambda repo, config: called.setdefault('output_dir', Path('/fake/out')))
    monkeypatch.setattr('runner._load_and_transform_gim_config', lambda repo, config: called.setdefault('gim_config', {'gim': {}, 'settings': {}}))
    monkeypatch.setattr('runner._run_plugins', lambda cfg, gim, out, dry_run=False: called.setdefault('ran_plugins', dry_run))

    run_build(Path('/repo'), Path('/config'), dry_run=True)

    assert called['scan']
    assert called['load_config'] == dummy_script_config
    assert called['output_dir'] == Path('/fake/out')
    assert called['gim_config'] == {'gim': {}, 'settings': {}}
    assert called['ran_plugins'] is True

def test_run_build_config_load_fail(monkeypatch):
    '''
    Should raise exception if _load_script_config fails.
    '''
    monkeypatch.setattr('runner._scan_and_import_plugins', lambda: None)
    monkeypatch.setattr('runner._load_script_config', lambda path: (_ for _ in ()).throw(RuntimeError('config error')))

    with pytest.raises(RuntimeError, match='config error'):
        run_build(Path('/repo'), Path('/config'))
