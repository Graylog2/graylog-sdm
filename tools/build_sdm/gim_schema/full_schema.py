from typing import Dict, Union, Any
from pydantic import BaseModel, root_validator
from .atomic_fields import GIMCategory
from build_sdm.base_output import OutputPlugin


class GIMFileWrapper(BaseModel):
    '''
    Represents a single GIM TOML file structure.

    Fields:
        type: Should be "gim" (required to recognize this as a GIM definition).
        category: A single key (like "file", "network", etc.) mapped to a GIMCategory object.
    '''
    type: str
    category: Dict[str, GIMCategory]


class TopLevelOutputPluginConfigWrapper(BaseModel):
    '''
    Represents optional plugin configs that are loaded alongside the GIM config. These
    provide configuration information for plugins that are related to the processing of
    GIM data, but do not fit inside the per-category configuration of the GIM.
    '''
    base: Dict[str, Any]

    @root_validator(pre=True)
    def validate_and_route(cls, values):
        plugin_name = values.get('base', {}).get('plugin_name')
        if not plugin_name:
            raise ValueError('Missing required "plugin_name" in [base] section.')

        plugin_class = OutputPlugin.registry.get(plugin_name)
        if not plugin_class:
            raise ValueError(f'No registered plugin found with name "{plugin_name}".')

        if not plugin_class.config_schema:
            raise ValueError(f'Plugin "{plugin_name}" does not define a config_schema.')

        # Validate the full config dict with the plugin's schema
        validated_config = plugin_class.config_schema(**values)
        return validated_config.dict()


class FullGIMConfig(BaseModel):
    '''
    Represents the top-level configuration containing multiple GIM config files.

    The dictionary maps filenames to their validated content (either GIM or generic dict).
    '''
    __root__: Dict[str, Union[GIMFileWrapper, dict]]
