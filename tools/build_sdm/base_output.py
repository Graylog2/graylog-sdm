import inspect
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Generic, Optional, Type, TypeVar
from pydantic import BaseModel

PluginConfigT = TypeVar('PluginConfigT', bound=BaseModel)


class OutputPlugin(ABC, Generic[PluginConfigT]):
    '''
    Abstract base class for output plugins.

    This class defines the interface and lifecycle for all output plugins.
    It enforces that each plugin implements a `generate` method and provides
    automatic subclass registration into a central registry for discovery.

    Type Parameters:
        PluginConfigT: The Pydantic BaseModel subclass used as the plugin's
            configuration type. Declare it by subclassing
            ``OutputPlugin[MyConfig]``.

    Attributes:
        enabled_by_default (bool): Indicates whether the plugin should be
            enabled by default if no explicit configuration is provided.
        config_schema (Optional[Type[BaseModel]]): Optional Pydantic model
            that defines the schema for plugin-specific configuration.
            Subclasses can assign their own schema to enable automatic
            validation of configuration dictionaries.
        registry (Dict[str, Type['OutputPlugin']]): Global plugin registry,
            mapping fully qualified class names (``<module>.<qualname>``)
            to plugin classes.
    '''
    enabled_by_default: bool = False
    config_schema: Optional[Type[BaseModel]] = None
    registry: Dict[str, Type['OutputPlugin']] = {}

    def __init__(self):
        '''
        Initialize the plugin instance.

        A logger is created and namespaced to the plugin’s class for
        structured and consistent logging. For example:
        'plugin.CsvOutputPlugin'.
        '''
        self.logger = logging.getLogger(f'plugin.{self.__class__.__name__}')

    def __init_subclass__(cls, **kwargs):
        '''
        Class initialization hook that runs automatically whenever
        a subclass of `OutputPlugin` is defined.

        This method ensures that concrete (non-abstract) subclasses
        are automatically registered in the plugin registry, making
        them discoverable at runtime.

        Args:
            **kwargs: Arbitrary keyword arguments forwarded by the class
                definition. Accepting **kwargs makes this method compatible
                with cooperative multiple inheritance patterns.

        Notes:
            - `inspect.isabstract(cls)` is used to filter out abstract
              subclasses that still have unimplemented abstract methods.
              These should not be instantiated or registered.
            - Registration keys use the fully qualified name
              (``<module>.<qualname>``) to avoid collisions when
              two plugins share the same simple class name but live in
              different modules.
            - `super().__init_subclass__(**kwargs)` ensures that other
              parent classes in a multiple inheritance chain also get
              their `__init_subclass__` methods invoked (MRO cooperation).
        '''
        super().__init_subclass__(**kwargs)

        # Skip registration if the subclass is abstract
        if not inspect.isabstract(cls):
            key = f'{cls.__module__}.{cls.__qualname__}'
            OutputPlugin.registry[key] = cls

    @abstractmethod
    def generate(
        self,
        gim_config: dict,
        output_dir: Path,
        plugin_config: Optional[PluginConfigT] = None
    ) -> None:
        '''
        Abstract method that all concrete plugins must implement.

        This method is the entry point for generating output based on the
        global configuration and optional plugin-specific settings.

        Args:
            gim_config (dict): Dictionary of the GIM (Graylog Information
                Model or equivalent) configuration data that defines the
                overall system context.
            output_dir (Path): Path object indicating where output files
                should be written.
            plugin_config (Optional[dict]): Optional dictionary of
                plugin-specific configuration parameters. This should be
                validated against the plugin’s `config_schema` if provided.

        Raises:
            NotImplementedError: If a subclass does not implement this method.
        '''
        raise NotImplementedError(
            'Subclasses of OutputPlugin must implement generate().'
        )

    def resolve_output_dir(
        self,
        default_dir: Path,
        repo_dir: Path,
        plugin_config: Optional[PluginConfigT] = None
    ) -> Path:
        '''
        Return the directory this plugin writes its output to.

        The runner calls this before generate(). The default is the runner's
        per-plugin directory, ``<output_dir>/<PluginClassName>/``. A plugin can
        override it to let its own config choose another location; when it does,
        output goes only there (it replaces the default, it doesn't add a copy).
        A CLI override passed to the runner takes precedence over this method.

        Args:
            default_dir: The runner's per-plugin default directory.
            repo_dir: Repository root, for resolving relative configured paths.
            plugin_config: This plugin's validated config, if any.

        Returns:
            The directory to pass to generate() as output_dir.
        '''
        return default_dir

    @classmethod
    def load_plugin_config(cls, config_dict: Dict[str, Any]) -> Optional[BaseModel]:
        '''
        Validate and load plugin-specific configuration, if a schema is defined.

        This class method allows a plugin to declare its own configuration
        schema (via Pydantic) and provides automatic validation of raw
        configuration dictionaries.

        Args:
            config_dict (Dict[str, Any]): Configuration dictionary parsed
                from a plugin config file (for example,
                `type = "config_output_plugin"` entries in TOML).

        Returns:
            Optional[BaseModel]: A validated Pydantic model instance if
            `config_schema` is defined. Returns None if the plugin does not
            declare a schema.

        Example:
            class CsvOutputPlugin(OutputPlugin):
                config_schema = CsvConfigModel  # subclass of BaseModel

            config = {"delimiter": ",", "quotechar": '"'}
            validated_config = CsvOutputPlugin.load_plugin_config(config)
        '''
        if cls.config_schema:
            return cls.config_schema(**config_dict)

        return None
