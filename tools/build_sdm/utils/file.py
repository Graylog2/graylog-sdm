import logging

from pathlib import Path


logger = logging.getLogger(__name__)

def write_file(target_file_path: Path, file_content: str, overwrite: bool = True) -> None:
    '''
    Write an output file and raise an exception if unable to.

    Args:
        target_file_path: Full path and file name to be written.
        file_content: Contents of the file to be created.
        overwrite: Flag to indicate if existing files should be overwritten. Default is True.

    Raises:
        OSError: If writing the file fails.
    '''
    try:
        # Ensure parent directories exist
        target_file_path.parent.mkdir(parents=True, exist_ok=True)

        # Handle overwrite behavior
        if target_file_path.exists() and not overwrite:
            logger.warning('Skipping writing file [%s] - found existing file', target_file_path)
            return

        # Guarantee exactly one newline at EOF
        file_content = file_content.rstrip('\n') + '\n'

        # Write file content
        target_file_path.write_text(file_content, encoding='utf-8')
        logger.debug('Successfully wrote output file [%s]', target_file_path)

    except OSError as e:
        logger.error('Failed to write output file [%s]: %s', target_file_path, e)
        raise
