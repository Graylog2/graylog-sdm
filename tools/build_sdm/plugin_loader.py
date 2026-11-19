import functools
import logging
import importlib
from build_sdm import output_plugins
import pkgutil
from build_sdm.base_output import OutputPlugin
from pydantic import ValidationError

#from output_plugins import __path__ as plugin_path

logger = logging.getLogger(__name__)

def safe_execute(method):
    '''
    Decorator that notes the plugin name on a plugin method's failure, then re-raises it.

    Plugin failures are fatal (ADR 0002): the error propagates so the build exits non-zero
    instead of finishing without the plugin's output. The CLI logs it once.
    '''
    @functools.wraps(method)
    def wrapper(*args, **kwargs):
        # A bound method (instance.generate) carries its plugin; an unbound one gets it first.
        plugin_instance = getattr(method, '__self__', None) or args[0]
        try:
            return method(*args, **kwargs)
        except Exception as e:
            e.add_note(f'in output plugin {plugin_instance.__class__.__name__}')
            raise

    return wrapper

def load_plugins_with_config(plugin_config: dict, mode='default_only'):
    '''
    Discover, instantiate, and return enabled output plugins with their validated configurations.

    This loader:
    - Searches for subclasses of OutputPlugin in the output_plugins package.
    - Uses each plugin's `enabled_by_default` flag or config override.
    - Validates plugin-specific config using its declared `config_schema`, if provided.
    - If validation fails for an enabled plugin, logs the errors and raises (plugin failures are fatal).

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
        module = importlib.import_module(f'{output_plugins.__name__}.{module_name}')
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
                            # The ValidationError text lists every invalid field.
                            e.add_note(f'in the configuration for output plugin {plugin_name}')
                            raise
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
