'''
Utilities for validating and sanitizing filenames or directory names.

These functions operate on individual name components, not full paths.
'''

import logging
import re

logger = logging.getLogger(__name__)

MIN_LENGTH = 3
VALID_PATTERN = re.compile(r'^[A-Za-z0-9_ ]+$', flags=re.ASCII)
INVALID_PATTERN = re.compile(r'[^A-Za-z0-9_ ]', flags=re.ASCII)
REPLACEMENT_CHAR = '_'


def _check_string_len(source_string: str) -> bool:
    '''
    Check whether a given string meets or exceeds the length defined by MIN_LENGTH.
    
    Args:
        source_string: The string to check.
        
    Returns:
        True if the string meets or exceeds the minimum length.
        
    Raises:
        ValueError: If the input is empty or shorter than MIN_LENGTH.
    '''
    if not source_string:
        raise ValueError('Value cannot be empty.')

    string_length = len(source_string)
    if string_length >= MIN_LENGTH:
        logger.debug('Validated string length: %d (min required %d)', string_length, MIN_LENGTH)
        return True

    raise ValueError(
        f'The value [{source_string}] is not long enough; its length '
        f'({string_length}) is less than the minimum of {MIN_LENGTH}.'
    )


def sanitize_string(source_string: str) -> str:
    '''
    Sanitize a filename or individual directory name by replacing invalid characters.
    This function does not sanitize entire paths.

    Args:
        source_string: The string to sanitize. Must be at least MIN_LENGTH characters.
        
    Returns:
        A sanitized version of the string that is safe to use for writing output files.

    Raises:
        ValueError: If the input is empty or shorter than MIN_LENGTH.
    '''
    _check_string_len(source_string)
    return INVALID_PATTERN.sub(REPLACEMENT_CHAR, source_string)


def check_string(source_string: str) -> bool:
    '''
    Check whether a given string is safe to use as a directory or filename.

    Args:
        source_string: The directory name or filename to check.
        
    Returns:
        True if the string is safe to use as a directory or filename, False otherwise.
        
    Raises:
        ValueError: If the input is empty or shorter than MIN_LENGTH.
    '''
    _check_string_len(source_string)
    return bool(VALID_PATTERN.fullmatch(source_string))
