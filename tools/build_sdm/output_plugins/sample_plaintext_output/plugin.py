# === Output Plugin Example with Detailed Documentation ===

# NOTE: There are companions to this sample plugin:
#       - config: 'sample_plaintext_output.toml' in the 'configs' dir
#       - unit test: 'test_sample_plaintext_output.py' in the 'tests' dir

import logging
from pathlib import Path
from typing import Optional, Dict, Any
from pydantic import BaseModel, Extra, Field, ValidationError
from build_sdm.base_output import OutputPlugin

# STEP 1: Define GLOBAL plugin configuration schema
# This class validates the [plugin] TOML config defined in `configs/`.

class PlainTextOutputConfig(BaseModel):
    '''
    Global settings for this output plugin. These control behavior across all categories.

    Fields:
        output_filename: Name of the output file this plugin will write.
        enabled: Whether this plugin is enabled by default if not overridden.
    '''
    output_filename: str = 'output.txt'
    enabled: bool = False


# STEP 2: Define PER-CATEGORY plugin configuration schema
# This is loaded from the GIM data TOML under each category's metadata section.
# These allow customizing behavior *per GIM category* (e.g., "network", "process").

class PlainTextOutputPluginConfig(BaseModel):
    '''
    Category-specific plugin configuration.

    This config is embedded within a GIM category TOML file at:
        [category.meta.plugin_config.{PluginName}]

    Example:
        [network.meta.plugin_config.PlainTextOutput]
        category_template_filename = "plaintext_template_file.txt"
    '''
    category_template_filename: Optional[str] = Field(
        None,
        description='Optional template to use for this specific category'
    )

    # Allow extra fields to support forward compatibility or plugin flexibility
    class Config:
        extra = Extra.allow


# STEP 3: Define optional TOP-LEVEL PLUGIN METADATA configuration
# These files contain plugin-specific data not tied to GIM categories, but to the plugin itself.
# Loaded from TOML files that declare: type = "config_output_plugin"

class TopLevelPluginConfig(BaseModel):
    '''
    Optional metadata for documentation generation or behavior hints.

    These values are loaded from files such as:
        plugin.config.plaintext.toml

    Keys correspond to top-level categories like 'gim' or 'field_schema', and
    might include things like section titles or descriptions to use in the
    output for those sections.
    '''
    gim: Optional[Dict[str, str]] = Field(
        None, description='Documentation metadata for GIM categories'
    )
    field_schema: Optional[Dict[str, str]] = Field(
        None, description='Documentation metadata for field schema definitions'
    )


# STEP 4: Define the plugin itself
# All plugins must inherit from `OutputPlugin`, which defines an abstract base interface.

class PlainTextOutput(OutputPlugin[PlainTextOutputConfig]):
    '''
    Example plugin that writes a plain-text representation of the GIM config to a file.

    This demonstrates:
    - Loading plugin config via Pydantic
    - Validating per-category settings
    - Emitting structured logs
    - Writing to disk using a plugin-defined output format
    '''

    # Whether the plugin is active by default if no specific config is given
    enabled_by_default = True

    # Pydantic model for validating the plugin's global config
    config_schema = PlainTextOutputConfig

    def __init__(self):
        '''
        Initialize the plugin and its associated logger.
        '''
        super().__init__()
        self.plugin_name = f'{self.__class__.__module__}.{self.__class__.__qualname__}'
        self.logger = logging.getLogger(self.plugin_name)

    def generate(
        self,
        gim_config: Dict[str, Any],
        output_dir: Path,
        plugin_config: Optional[PlainTextOutputConfig] = None
    ) -> None:
        '''
        Main entry point for plugin output generation.

        Args:
            gim_config: The full loaded GIM config tree.
            output_dir: Directory to write output files to.
            plugin_config: Validated instance of global config for this plugin.
        '''
        plugin_config = (
            plugin_config if isinstance(plugin_config, PlainTextOutputConfig)
            else PlainTextOutputConfig()
        )

        self.logger.debug('Generating plain text output with config: %s', plugin_config)

        # Optionally process per-category configs (if needed)
        for category, category_data in gim_config.get('gim', {}).items():
            raw_plugin_config = (
                category_data.get('meta', {})
                .get('plugin_config', {})
                .get(self.plugin_name, {})
            )
            try:
                category_config = PlainTextOutputPluginConfig(**raw_plugin_config)
                self.logger.debug('Using category config for %s: %s', category, category_config)
            except ValidationError as e:
                # Plugin failures are fatal (ADR 0002): note the category and let the build fail.
                e.add_note(f'in plain text plugin config for category [{category}]')
                raise

        # Determine the final output path
        output_path = output_dir / plugin_config.output_filename

        with output_path.open('w', encoding='utf-8') as f:
            f.write('=== GIM CONFIG DUMP ===\n\n')
            for key, value in gim_config.items():
                f.write(f'{key}:\n{value}\n\n')
        self.logger.info('Saved plain text output to: %s', output_path)

        self.logger.debug('Plugin processing completed.')
