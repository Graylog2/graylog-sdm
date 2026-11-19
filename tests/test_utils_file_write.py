import pytest
import tempfile
import os

from pathlib import Path
from unittest.mock import patch

from build_sdm.utils.file import write_file  # Adjust import path to your actual module


def test_write_file_creates_file(tmp_path):
    '''
    Should successfully create a new file and write the provided content.
    '''
    target = tmp_path / 'test_output.txt'
    content = 'hello world\n'

    write_file(target, content)

    assert target.exists()
    assert target.read_text(encoding='utf-8') == content


def test_write_file_creates_nested_dirs(tmp_path):
    '''
    Should create nested directories automatically when writing a file.
    '''
    target = tmp_path / 'deep' / 'nested' / 'path' / 'output.txt'
    content = 'nested write\n'

    write_file(target, content)

    assert target.exists()
    assert target.read_text(encoding='utf-8') == content
    # Confirm directories were created
    assert (tmp_path / 'deep' / 'nested' / 'path').is_dir()


def test_write_file_skips_existing_when_overwrite_false(tmp_path, caplog):
    '''
    Should skip writing if file exists and overwrite is False.
    '''
    target = tmp_path / 'existing.txt'
    original_content = 'original data'
    target.write_text(original_content, encoding='utf-8')

    # Call again with overwrite=False
    write_file(target, 'new data', overwrite=False)

    # Ensure content was NOT replaced
    assert target.read_text(encoding='utf-8') == original_content

    # Check warning log was emitted
    assert any('Skipping writing file' in msg for msg in caplog.messages)


def test_write_file_raises_oserror(monkeypatch, tmp_path):
    '''
    Should log and raise OSError if the write operation fails.
    '''
    target = tmp_path / 'failing.txt'

    def fake_write_text(*args, **kwargs):
        raise OSError('Disk full')

    # Monkeypatch Path.write_text to simulate a disk write failure
    monkeypatch.setattr(Path, 'write_text', fake_write_text)

    with pytest.raises(OSError, match='Disk full'):
        write_file(target, 'test')

    # Ensure the function created the parent directory before failing
    assert target.parent.exists()


def test_write_file_failure_propagates_without_logging(monkeypatch, tmp_path, caplog):
    '''
    Should raise when file writing fails, without logging: the CLI logs the failure once.
    '''
    target = tmp_path / 'failing.txt'

    def fake_write_text(*args, **kwargs):
        raise OSError('Permission denied')

    monkeypatch.setattr(Path, 'write_text', fake_write_text)

    with pytest.raises(OSError, match='Permission denied'):
        write_file(target, 'content')

    assert not [r for r in caplog.records if r.levelname == 'ERROR']
