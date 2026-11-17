import logging
from build_sdm.base_output import OutputPlugin
from pathlib import Path
from tomlkit import parse, items
from typing import Union, Dict, Any, Optional, Set
from pydantic import ValidationError
from build_sdm.gim_schema.full_schema import GIMFileWrapper
from build_sdm.gim_schema.field_schema_model import FieldSchemaDocument, ConfigDocument

logger = logging.getLogger(__name__)


def _normalize_toml(obj):
    '''
    Recursively normalize a TOML-parsed object by converting tomlkit types
    (e.g., tomlkit.items.Array, String, Integer) into standard Python types.

    This ensures compatibility with systems such as Pydantic and serialization
    routines that expect dicts, lists, strings, etc., not tomlkit wrappers.

    Args:
        obj: A TOML-parsed object (dict, list, tomlkit item).

    Returns:
        The equivalent native Python structure (e.g., dict, list, str, int, etc.).
    '''
    if isinstance(obj, dict):
        return {k: _normalize_toml(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_normalize_toml(v) for v in obj]
    elif isinstance(obj, items.Array):
        return [_normalize_toml(v) for v in obj]
    elif isinstance(obj, items.String):
        return str(obj)
    elif isinstance(obj, items.Integer):
        return int(obj)
    elif isinstance(obj, items.Float):
        return float(obj)
    elif isinstance(obj, items.Bool):
        return bool(obj)
    elif isinstance(obj, (items.Date, items.DateTime)):
        return str(obj)
    elif isinstance(obj, items.Table):
        # Convert tomlkit table to dict and recurse
        return _normalize_toml(dict(obj))
    return obj  # Return primitive values unchanged


def _parse_toml_file(file: Path) -> dict:
    '''
    Parse a TOML file into a fully normalized Python dictionary.

    This function reads a TOML file using `tomlkit.parse` to preserve structure
    and comments if needed, then recursively normalizes the result to convert
    tomlkit-specific types into plain Python types.

    Args:
        file: Path to the TOML file to parse.

    Returns:
        A fully normalized dictionary suitable for use with Pydantic or JSON serialization.
    '''
    with file.open('r', encoding='utf-8') as f:
        parsed = parse(f.read())
    return _normalize_toml(parsed)


def _process_gim_file(file: Path, raw_data: dict) -> dict:
    '''
    Validate and return parsed data from a GIM configuration file.

    Args:
        file: Path to the TOML file being processed.
        raw_data: Parsed TOML dictionary expected to contain type = 'gim'.

    Returns:
        A dictionary with merged GIM category data, including the 'type' field.

    Raises:
        ValidationError: If the file does not conform to the GIMFileWrapper schema.
    '''
    payload = {
        'type': raw_data['type'],
        'category': {k: v for k, v in raw_data.items() if k != 'type'}
    }
    validated = GIMFileWrapper.parse_obj(payload)
    parsed_data = validated.category
    typed_data = {'type': 'gim'}
    typed_data.update(parsed_data)
    return typed_data


def _process_plugin_file(file: Path, raw_data: dict) -> dict:
    ''''
    Validate and return parsed plugin configuration data.

    Args:
        file: Path to the TOML file being processed.
        raw_data: Parsed TOML dictionary with type = 'config_output_plugin'.

    Returns:
        A dictionary with plugin name as key and validated configuration as value.

    Raises:
        ValueError: If plugin_name is missing or plugin class is unregistered.
        ValidationError: If plugin config fails schema validation.
    '''
    if 'base' not in raw_data or 'plugin_name' not in raw_data['base']:
        raise ValueError('Missing [base] section or plugin_name field')
    plugin_name = raw_data['base']['plugin_name']
    plugin_cls = OutputPlugin.registry.get(plugin_name)
    if not plugin_cls:
        raise ValueError(f'No plugin registered with name: {plugin_name}')
    validated = plugin_cls.load_plugin_config(raw_data)
    return {
        'type': 'config_output_plugin',
        'plugin': {plugin_name: validated}
    }


def _process_field_schema_file(file: Path, raw_data: dict) -> dict:
    '''
    Validate and return parsed data from a field_schema file.

    Args:
        file: Path to the TOML file.
        raw_data: Parsed TOML dict (must contain type = "field_schema").

    Returns:
        A dict shaped like {'type': 'field_schema', <entity_name>: {...}}
        which flattens away the extra 'entities' level.
    '''
    try:
        validated = FieldSchemaDocument.parse_obj(raw_data)

        # ❶ Flatten: merge each entity directly into the result dict
        flattened: Dict[str, Any] = {'type': 'field_schema'}
        flattened.update(validated.entities)          # removes the “entities” key

        return flattened

    except ValidationError as e:
        raise ValueError(f'field_schema validation failed in {file.name}:\n{e}')


def _process_config_items(file: Path, raw_data: dict) -> ConfigDocument:
    '''
    Validate and return data from a parsed GIM configuration file.

    Args:
        file: Path to the TOML file.
        raw_data: Parsed TOML dict (must contain type = "field_schema").

    Returns:
        A dict shaped like {'type': 'config', <entity_name>: {...}}
        which flattens away the extra 'entities' level.
    '''
    try:
        validated = ConfigDocument.parse_obj(raw_data)
        return validated
    except ValidationError as e:
        raise ValueError(f'field_schema_config validation failed in {file.name}:\n{e}')


def _merge_or_store(result: dict, file: Path, data: dict, merge: bool) -> None:
    '''
    Either merge parsed data into the result dict or store it by filename.

    Args:
        result: Dictionary where results are being accumulated.
        file: The TOML file currently being processed.
        data: Parsed and validated data from that file.
        merge: If True, merge data into result; otherwise, store by file name.
    '''
    if merge:
        if data.get('type') == 'config_output_plugin':
            plugin_data = data.get('plugin', {})
            for k, v in plugin_data.items():
                result.setdefault('plugin', {})[k] = v
        else:
            result.update({k: v for k, v in data.items() if k != 'type'})
    else:
        result[file.name] = data


def load_gim_config_files(
        directory: Union[str, Path],
        merge: bool = False,
        only_types: Optional[Set[str]] = None
    ) -> dict:
    '''
    Load and validate all GIM config files in a directory.

    If any file fails to parse or validate, execution halts with a ValueError.

    Args:
        directory: Path to the config folder.
        merge: Whether to merge all valid data into a single dict.
        only_types: If given, load only files whose `type` is in this set and skip
            all other files silently (e.g. to read config_output_plugin files from
            a directory that also holds untyped script config files).

    Returns:
        Dictionary of validated data.

    Raises:
        ValueError: If any file fails to parse or validate.
    '''
    directory = Path(directory).expanduser().resolve()
    # Sorted so that load order, and with it the order of every output, does not depend
    # on the order the filesystem lists files in.
    toml_files = sorted([*directory.rglob('*.toml'), *directory.rglob('*.tml')])
    if not toml_files:
        raise FileNotFoundError(f'No .toml or .tml files found in {directory}')

    result = {}
    errors = []

    for file in toml_files:
        try:
            raw_data = _parse_toml_file(file)
        except Exception as e:
            msg = f'Unable to parse file {file}: {e}'
            logger.error(msg)
            errors.append(msg)
            continue

        entry_type = raw_data.get('type')
        if only_types is not None and entry_type not in only_types:
            continue
        if not entry_type:
            logger.warning('No type defined in file %s, skipping file', file.name)
            continue

        try:
            if entry_type == 'gim':
                data = _process_gim_file(file, raw_data)
            elif entry_type == 'config_output_plugin':
                data = _process_plugin_file(file, raw_data)
            elif entry_type == 'field_schema':
                data = _process_field_schema_file(file, raw_data)
            elif entry_type == 'config':
                data = _process_config_items(file, raw_data)
            else:
                logger.warning('No schema defined for configuration type %s in file %s', entry_type, file.name)
                continue

            _merge_or_store(result, file, data, merge)
        except (ValidationError, ValueError) as e:
            logger.error('Validation error in file %s: %s', file.name, e)
            errors.append(f'{file.name}: {e}')

    if errors:
        logger.fatal('One or more configuration files failed validation or parsing.')
        raise ValueError('GIM configuration aborted due to validation errors.')

    return result


def load_script_config_files(config_dir: Path) -> dict:
    '''
    Load and parse all .toml/.tml script configuration files. These are the configuration files that
    will manage how build-sdm operates, including the plugins.

    Args:
        config_dir: Directory path as Path.

    Returns:
        dict containing merged or per-file parsed TOML data.
    '''
    config_dir = Path(config_dir).expanduser().resolve()
    config_files = sorted([*config_dir.rglob('*.toml'), *config_dir.rglob('*.tml')])

    try:
        config = {'plugins': {}, 'global': {}}
        for file in config_files:
            logger.debug('Loading script config file %s', file)
            with file.open('r', encoding='utf-8') as f:
                snippet = parse(f.read())
            if 'plugin' in snippet:
                plugin_name = snippet['plugin']['name']
                config['plugins'][plugin_name] = snippet['plugin']
            elif 'global' in snippet:
                config['global'].update(snippet['global'])
    except Exception as e:
        logger.fatal('Unable to load configuration from %s', config_dir)
        return {}

    return config
