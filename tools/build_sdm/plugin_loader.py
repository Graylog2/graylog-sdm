import functools
import logging
import importlib
import output_plugins
import pkgutil
import traceback
from base_output import OutputPlugin
from pydantic import ValidationError

#from output_plugins import __path__ as plugin_path

logger = logging.getLogger(__name__)

def safe_execute(method):
    '''
    Decorator to safely execute a plugin method, catching and logging any unexpected errors.
    '''
    @functools.wraps(method)
    def wrapper(*args, **kwargs):
        plugin_instance = args[0]
        try:
            return method(*args, **kwargs)
        except Exception as e:
            logger.error(f'[{plugin_instance.__class__.__name__}] Plugin execution failed: {str(e)}')
            logger.warning(f'[{plugin_instance.__class__.__name__}] Skipping this plugin due to runtime error.')

            if logger.isEnabledFor(logging.DEBUG):
                tb = traceback.format_exc()
                logger.debug(f'[{plugin_instance.__class__.__name__}] Full traceback:\n{tb}')

    return wrapper

def load_plugins_with_config(plugin_config: dict, mode='default_only'):
    '''
    Discover, instantiate, and return enabled output plugins with their validated configurations.

    This loader:
    - Searches for subclasses of OutputPlugin in the output_plugins package.
    - Uses each plugin's `enabled_by_default` flag or config override.
    - Validates plugin-specific config using its declared `config_schema`, if provided.
    - If validation fails for a plugin, logs the error and skips loading that plugin.

    Args:
        plugin_configs: A dictionary mapping plugin names to their config snippets.
        mode: One of:
            'default_only' - Load only plugins where config["enabled"] is True or plugin.enabled_by_default is True
            'all'          - Load all discovered plugins regardless of default

    Returns:
        A list of (plugin_instance, validated_config) tuples.
    '''
    plugins = []

    for _, module_name, _ in pkgutil.iter_modules(output_plugins.__path__):
        module = importlib.import_module(f'output_plugins.{module_name}')
        for attr in dir(module):
            cls = getattr(module, attr)
            if isinstance(cls, type) and issubclass(cls, OutputPlugin) and cls is not OutputPlugin:
                plugin_name = cls.__name__
                config = plugin_config.get(plugin_name, {})
                enabled = config.get('enabled', cls.enabled_by_default)

                logger.debug('[%s] Found output plugin module', plugin_name)

                if mode == 'all' or enabled:
                    validated_config = None

                    logger.debug('[%s] Plugin module is enabled', plugin_name)

                    if cls.config_schema:
                        logger.debug('[%s] has a config_schema enabled', plugin_name)
                        try:
                            validated_config = cls.config_schema.parse_obj(config)
                        except ValidationError as e:
                            logger.error(
                                '[%s] Invalid configuration for plugin detected',
                                plugin_name
                                )
                            for error in e.errors():
                                field = '.'.join(str(loc) for loc in error['loc'])
                                logger.error(
                                    '[%s] Field [%s]: %s',
                                    plugin_name, field, error['msg']
                                    )
                            logger.error('[%s] Skipping this plugin', plugin_name)
                            continue
                    else:
                        logger.debug('[%s] has no config_schema defined', plugin_name)
                        validated_config = config

                    logger.info('Loading output plugin module %s', plugin_name)
                    instance = cls()

                    # Wrap instance.generate with the safe_execute wrapper
                    instance.generate = safe_execute(instance.generate)

                    plugins.append((instance, validated_config))
                else:
                    logger.debug('[%s] Output plugin module not enabled', plugin_name)

    return plugins
