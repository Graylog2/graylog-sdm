import pytest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from build_sdm.runner import _ensure_output_dir

def test_ensure_output_dir_creates_directory():
    '''
    Verify that _ensure_output_dir creates the output directory when it does not exist.
    '''
    with TemporaryDirectory() as tmp_dir_name:
        repo_dir = Path(tmp_dir_name)
        output_dir = repo_dir / 'build' / 'sdm_artifacts'

        script_config = {
            'global': {}  # no output_dir key present, should default
        }

        result = _ensure_output_dir(repo_dir, script_config)

        assert result == output_dir
        assert output_dir.is_dir()


def test_ensure_output_dir_uses_configured_path():
    '''
    Verify that _ensure_output_dir uses the configured output_dir if provided in script_config.
    '''
    with TemporaryDirectory() as tmp_base_dir:
        custom_output_path = Path(tmp_base_dir) / 'custom_output'

        script_config = {
            'global': {
                'output_dir': str(custom_output_path)
            }
        }

        result_path = _ensure_output_dir(Path('/dummy/repo'), script_config)

        assert result_path == custom_output_path
        assert result_path.exists()
        assert result_path.is_dir()


def test_ensure_output_dir_success():
    '''
    Should create the output directory and return the resolved path.
    '''
    with TemporaryDirectory() as tmp_dir_name:
        repo_dir = Path(tmp_dir_name)
        script_config = {'global': {'output_dir': 'custom/output'}}

        result = _ensure_output_dir(repo_dir, script_config)

        expected_dir = repo_dir / 'custom' / 'output'
        assert result == expected_dir
        assert expected_dir.is_dir()


def test_ensure_output_dir_failure(caplog):
    '''
    Should raise an exception and log an error if mkdir fails.
    '''
    script_config = {'global': {'output_dir': 'fail/here'}}
    repo_dir = Path('/repo/root')

    with patch.object(Path, 'mkdir', side_effect=OSError('Permission denied')):
        with pytest.raises(OSError, match='Permission denied'):
            _ensure_output_dir(repo_dir, script_config)

    assert any('Error creating output directory' in message for message in caplog.messages)
