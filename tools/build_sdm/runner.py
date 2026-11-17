# runner.py
import logging
import importlib
import pkgutil
from pathlib import Path
from typing import Any, Dict

from config_loader import load_gim_config_files, load_script_config_files
from gim_schema.sub_fields import validate_applies_to
from plugin_loader import load_plugins_with_config
from utils.serialization import to_serializable
from utils.transform import restructure_gim_config
import output_plugins


logger = logging.getLogger(__name__)

def run_build(repo_dir: Path, config_dir: Path, dry_run: bool = False) -> None:
    '''
    Main entry point for building GIM documentation and artifacts.
    '''
    _scan_and_import_plugins()
    script_config = _load_script_config(config_dir)

    output_dir = _ensure_output_dir(repo_dir, script_config)
    gim_config = _load_and_transform_gim_config(repo_dir, script_config)

    #_run_plugins(script_config, gim_config, output_dir)
    _run_plugins(script_config, gim_config, output_dir, dry_run=dry_run)

# --- Helper functions below ---

def _scan_and_import_plugins() -> None:
    for _, name, _ in pkgutil.walk_packages(output_plugins.__path__, output_plugins.__name__ + '.'):
        importlib.import_module(name)

def _load_script_config(config_dir: Path) -> Dict[str, Any]:
    logger.debug('Attempting to load script config from %s', config_dir)
    script_config = load_script_config_files(config_dir)

    if not (script_config.get('global') and script_config.get('plugins')):
        logger.fatal('No script configuration was read, exiting.')
        raise RuntimeError('Invalid or missing script config.')

    return script_config


def _ensure_output_dir(repo_dir: Path, script_config: Dict[str, Any]) -> Path:
    output_subdir = script_config.get('global', {}).get('output_dir') or 'build/generated_outputs'
    output_dir = repo_dir / Path(output_subdir)

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.fatal('Error creating output directory %s: %s', output_dir, e)
        raise

    logger.info('Saving output to %s', output_dir)
    return output_dir


def _load_and_transform_gim_config(repo_dir: Path, script_config: Dict[str, Any]) -> Dict[str, Any]:
    '''Load, validate, and restructure the GIM source TOML tree into gim_config.

    Resolves the GIM source directory from script_config, loads and validates
    every TOML file under it (via config_loader), restructures the result from
    a file-oriented layout into the type/category-oriented gim_config shape
    consumed by output plugins, and validates that every sub-field entity's
    applies_to list references a real "top" entity.

    Args:
        repo_dir: Repository root, used to resolve a relative gim_source_dir.
        script_config: Loaded script configuration; script_config['global']
            may set 'gim_source_dir' (defaults to '_meta/gim').

    Returns:
        The restructured gim_config dict (keys like 'gim', 'field_schema',
        'config', 'settings') passed to every output plugin's generate().

    Raises:
        NotADirectoryError: If the resolved GIM source directory doesn't exist.
        ValueError: If any GIM TOML file fails validation, or a sub-field
            entity's applies_to references an entity that isn't a known "top"
            entity.
    '''
    gim_dir = Path(script_config['global'].get('gim_source_dir') or '_meta/gim')
    gim_dir = repo_dir / gim_dir

    if not gim_dir.is_dir():
        logger.fatal('Path %s is not a directory', gim_dir)
        raise NotADirectoryError(f'GIM directory not found: {gim_dir}')

    try:
        gim_config = load_gim_config_files(gim_dir, merge=False)
    except Exception as e:
        logger.fatal('Unable to load GIM source data from %s, error: %s', gim_dir, e)
        raise

    gim_config['settings'] = {'type': 'config', 'gim_dir': str(gim_dir)}

    serialized = to_serializable(gim_config)
    restructured = restructure_gim_config(serialized)
    validate_applies_to(restructured.get('field_schema', {}))
    return restructured


def _run_plugins(
        script_config: Dict[str, Any],
        gim_config: Dict[str, Any],
        output_dir: Path,
        dry_run: bool=False
    ) -> None:
    logger.debug('Scanning and loading output plugin modules')
    plugins = load_plugins_with_config(script_config['plugins'], mode='default_only')

    logger.debug('Invoking output plugins')
    for plugin, validated_plugin_config in plugins:
        if dry_run:
            plugin.logger.info(
                '[DRY RUN] Would generate output using plugin: %s',
                plugin.__class__.__name__
                )
        else:
            plugin_output_dir = output_dir / plugin.__class__.__name__
            plugin_output_dir.mkdir(parents=True, exist_ok=True)

            plugin.generate(
                gim_config,
                output_dir=plugin_output_dir,
                plugin_config=validated_plugin_config
            )
