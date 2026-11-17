'''
Unit tests for sanitize_utils.py

These tests validate correct behavior of:
- _check_string_len
- sanitize_string
- check_string

Assumes MIN_LENGTH = 3.
'''

import pytest


from build_sdm.utils import sanitize as s


# --- _check_string_len -------------------------------------------------------

def test_check_string_len_valid_length():
    '''Should return True for strings meeting or exceeding MIN_LENGTH.'''
    assert s._check_string_len('abc') is True
    assert s._check_string_len('abcd') is True


def test_check_string_len_too_short_raises():
    '''Should raise ValueError for strings shorter than MIN_LENGTH.'''
    with pytest.raises(ValueError) as excinfo:
        s._check_string_len('ab')
    assert 'not long enough' in str(excinfo.value)


def test_check_string_len_empty_raises():
    '''Should raise ValueError for empty string.'''
    with pytest.raises(ValueError) as excinfo:
        s._check_string_len('')
    assert 'empty' in str(excinfo.value).lower()


# --- sanitize_string ---------------------------------------------------------

def test_sanitize_string_valid_input_returns_same_value():
    '''Strings already valid should be returned unchanged.'''
    assert s.sanitize_string('abc') == 'abc'
    assert s.sanitize_string('valid name_123') == 'valid name_123'


def test_sanitize_string_replaces_invalid_chars():
    '''Should replace invalid characters with REPLACEMENT_CHAR.'''
    dirty = 'bad/name?here'
    expected = 'bad_name_here'.replace('/', s.REPLACEMENT_CHAR).replace('?', s.REPLACEMENT_CHAR)
    result = s.sanitize_string(dirty)
    assert result == expected
    assert s.REPLACEMENT_CHAR in result


def test_sanitize_string_too_short_raises():
    '''Should raise ValueError if shorter than MIN_LENGTH.'''
    with pytest.raises(ValueError):
        s.sanitize_string('ab')


def test_sanitize_string_empty_raises():
    '''Should raise ValueError for empty string.'''
    with pytest.raises(ValueError):
        s.sanitize_string('')


# --- check_string ------------------------------------------------------------

def test_check_string_valid_strings_return_true():
    '''Valid strings should return True.'''
    assert s.check_string('abc') is True
    assert s.check_string('Valid_Name 123') is True


def test_check_string_invalid_strings_return_false():
    '''Strings with invalid characters should return False.'''
    assert s.check_string('bad/name') is False
    assert s.check_string('invalid!') is False


def test_check_string_too_short_raises():
    '''Should raise ValueError for too-short strings.'''
    with pytest.raises(ValueError):
        s.check_string('ab')


def test_check_string_empty_raises():
    '''Should raise ValueError for empty input.'''
    with pytest.raises(ValueError):
        s.check_string('')
