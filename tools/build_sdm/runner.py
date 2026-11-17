# runner.py
import logging
import importlib
import pkgutil
from pathlib import Path
from typing import Any, Dict, Optional

from build_sdm.config_loader import load_gim_config_files, load_script_config_files
from build_sdm.gim_schema.sub_fields import validate_applies_to
from build_sdm.plugin_loader import load_plugins_with_config
from build_sdm.utils.serialization import to_serializable
from build_sdm.utils.transform import restructure_gim_config
from build_sdm import output_plugins


logger = logging.getLogger(__name__)

def run_build(repo_dir: Path, config_dir: Path, dry_run: bool = False) -> None:
    '''
    Main entry point for building GIM documentation and artifacts.
    '''
    _scan_and_import_plugins()
    script_config = _load_script_config(config_dir)

    output_dir = _ensure_output_dir(repo_dir, script_config)
    gim_config = _load_and_transform_gim_config(repo_dir, script_config, config_dir)

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
    output_subdir = script_config.get('global', {}).get('output_dir') or 'build/sdm_artifacts'
    output_dir = repo_dir / Path(output_subdir)

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.fatal('Error creating output directory %s: %s', output_dir, e)
        raise

    logger.info('Saving output to %s', output_dir)
    return output_dir


def _load_and_transform_gim_config(
        repo_dir: Path,
        script_config: Dict[str, Any],
        config_dir: Optional[Path] = None
    ) -> Dict[str, Any]:
    '''Load, validate, and restructure the GIM source TOML tree into gim_config.

    Resolves the GIM source directory from script_config, loads and validates
    every TOML file under it (via config_loader), restructures the result from
    a file-oriented layout into the type/category-oriented gim_config shape
    consumed by output plugins, and validates that every sub-field entity's
    applies_to list references a real "top" entity.

    Args:
        repo_dir: Repository root, used to resolve a relative sdm_source_dir.
        script_config: Loaded script configuration; script_config['global']
            may set 'sdm_source_dir' (defaults to 'src/sdm').
        config_dir: Script config directory. Files in it with
            type = "config_output_plugin" (presentation config such as
            plugin.config.madcap.toml) are loaded alongside the SDM source data.

    Returns:
        The restructured gim_config dict (keys like 'gim', 'field_schema',
        'config', 'settings') passed to every output plugin's generate().

    Raises:
        NotADirectoryError: If the resolved GIM source directory doesn't exist.
        ValueError: If any GIM TOML file fails validation, or a sub-field
            entity's applies_to references an entity that isn't a known "top"
            entity.
    '''
    source_dir_setting = Path(script_config['global'].get('sdm_source_dir') or 'src/sdm')
    gim_dir = repo_dir / source_dir_setting

    if not gim_dir.is_dir():
        logger.fatal('Path %s is not a directory', gim_dir)
        raise NotADirectoryError(f'GIM directory not found: {gim_dir}')

    try:
        gim_config = load_gim_config_files(gim_dir, merge=False)
    except Exception as e:
        logger.fatal('Unable to load GIM source data from %s, error: %s', gim_dir, e)
        raise

    if config_dir is not None:
        gim_config.update(
            load_gim_config_files(config_dir, merge=False, only_types={'config_output_plugin'})
        )

    # Record the configured (repo-relative) path, not the absolute one, so the output
    # is the same on every checkout.
    gim_config['settings'] = {'type': 'config', 'gim_dir': source_dir_setting.as_posix()}

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
