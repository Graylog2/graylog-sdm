import re

from pydantic import BaseModel, Field, Extra, StrictStr, constr, validator
from typing import Optional, Dict, List

# Where generated pages find the Flare project's Content/Resources/ folder (ADR 0007): every
# page sits one directory below the output root, which is Content/SDM/.
DEFAULT_RESOURCES_PATH = '../../Resources'

# resources_path is inserted verbatim into href attributes and single-quoted CSS url()s, and the
# .j2 templates aren't autoescaped. Allow only '/'-separated segments of letters, digits, '.',
# '_', '-' and spaces, so no value can break the markup (no '&', quotes, '<', '%', backslash or ':').
_RESOURCES_PATH_PATTERN = re.compile(r'[A-Za-z0-9._ -]+(?:/[A-Za-z0-9._ -]+)*/?')

# Allow only letters, digits, and underscores
SafeSubdir = Optional[constr(regex=r'^[A-Za-z0-9_ ]+$')]


class MadcapHtmlOutputConfig(BaseModel):
    '''
    Global configuration for the MadcapHtmlOutput plugin, loaded from this
    plugin's top-level config_output_plugin base section (or defaulted when
    absent).

    default_field_columns and default_subfield_columns set the default column
    order for a field_schema entity's main fields table and its "Sub-fields"
    table (composed from sub-field entities' applies_to relationships),
    respectively. Either can be overridden per entity via
    MadcapHtmlOutputPluginConfig's field_column_order/subfield_column_order.
    '''
    enabled: bool = False
    output_dir: Optional[str] = Field(
        None,
        description='Optional output directory for the HTML. Replaces the default '
                    '<output_dir>/MadcapHtmlOutput/; a relative path resolves against the '
                    'repository root. The build-sdm --madcap-output-dir flag overrides it.'
    )
    resources_path: StrictStr = Field(
        DEFAULT_RESOURCES_PATH,
        description='Path from a generated page to the Flare Resources/ folder, used for every '
                    'stylesheet and table-style link. Relative, with forward slashes; letters, digits, '
                    '".", "_", "-" and spaces only.'
    )
    default_field_columns: Optional[List[str]] = Field(
        default_factory=lambda: ['field_suffix', 'field_type', 'description', 'example_values'],
        description='Default column order for rendering field rows in entity templates'
    )
    default_subfield_columns: Optional[List[str]] = Field(
        default_factory=lambda: ['field', 'field_type', 'description', 'example_values'],
        description='Default column order for rendering the sub-fields table on entity templates'
    )

    @validator('resources_path')
    def _relative_resources_path(cls, value: str) -> str:
        '''
        Require a relative, forward-slash path of safe characters; drop any trailing slash.
        '''
        if not _RESOURCES_PATH_PATTERN.fullmatch(value):
            raise ValueError(
                "resources_path must be a relative path of '/'-separated segments using only "
                "letters, digits, '.', '_', '-' and spaces"
            )
        return value.rstrip('/')


class MadcapHtmlOutputPluginConfig(BaseModel):
    '''
    Validate the per-entity plugin configuration that may be set in a GIM
    category or field_schema TOML file's
    [<entity>.meta.plugin_config.MadcapHtmlOutput] section, overriding this
    plugin's global MadcapHtmlOutputConfig defaults for that entry.

    category_template_filename and entity_template_filename select the Jinja
    template used to render a GIM category page or a field_schema entity page,
    respectively. field_column_order and subfield_column_order override the
    default column order for a field_schema entity's main fields table and its
    "Sub-fields" table, respectively.
    '''
    category_template_filename: Optional[StrictStr] = Field(
        'gim_category_template.j2',
        description='Template name to use for this category'
    )
    entity_template_filename: Optional[StrictStr] = Field(
        'field_schema_entity_template.j2',
        description='Template name to use for this field_schema entity'
    )
    field_column_order: Optional[List[str]] = Field(
        None,
        description='Optional override for field table column order in this entity'
    )
    subfield_column_order: Optional[List[str]] = Field(
        None,
        description='Optional override for the sub-fields table column order in this entity'
    )

    class Config:
        extra = Extra.allow


class TopLevelGimPluginMetadata(BaseModel):
    '''
    The "Top level" GIM metadata is an optional configuration file stored in the GIM
    configuration data that provides specific configuration data for plugins. This
    allows for plugin configuration data that is associated with the GIM configuration
    data being processed.

    This specific section is used to identify the plugin the configuration data is
    designed for.
    '''
    plugin_name: str


class TopLevelGimSectionMetadata(BaseModel):
    '''
    The "Top Level" GIM metadata is an optional configuration file stored in the GIM
    configuration data that provides specific configuration data for plugins. This
    allows for plugin configuration data that is associated with the GIM configuration
    data being processed.

    This specific section is the "gim" section, which is related
    to the top-level page that will be generated for GIM artifacts. The structure is:

    type = "config_output_plugin"

    [base]
    plugin_name = "output_plugin.madcap_html_output.MadcapHtmlOutput"

    [gim]
    title = "..."
    intro = "..."
    template = "gim_category_top_template.j2"  # Optional: will default if omitted
    output_filename = "GIM_Categories.html" # Default top-level output filename
    html_output_subdir = "gim" # optional, will use section name if omitted
    '''
    title: str
    intro: str
    template: str = 'gim_category_top_template.j2'
    output_filename: str = 'GIM_Categories.html'
    html_output_subdir: SafeSubdir = Field(
        None,
        description='Optional subdirectory for output HTML files (letters, digits, and underscores only)'
    )


class TopLevelFieldSchemaSectionMetadata(BaseModel):
    '''
    This class defines the structure of the "field_schema" section within a top-level
    plugin configuration TOML file of type "config_output_plugin". It represents metadata
    used to generate a top-level documentation page for normalized field schemas.

    This configuration is intended for use by output plugins (such as MadcapHtmlOutput)
    that generate documentation or other artifacts from GIM schema definitions. It allows
    customization of the page title, introductory text, and template used to render the
    field schema reference page.

    Example TOML structure:

    type = "config_output_plugin"

    [base]
    plugin_name = "output_plugin.madcap_html_output.MadcapHtmlOutput"

    [field_schema]
    title = "Field Schema Reference"
    intro = "This section describes normalized schema fields used in structured events."
    template = "field_schema_top_template.j2"  # Optional; will default if omitted
    html_output_subdir = "field_schema" #Optional; will use section name if omitted
    '''
    title: str
    intro: str
    template: str = 'field_schema_top_template.j2'
    output_filename: str = 'Schema_Entities.html'
    html_output_subdir: SafeSubdir = Field(
        None,
        description='Optional subdirectory for output HTML files (letters, digits, and underscores only)'
    )


class MadcapTopLevelConfig(BaseModel):
    '''
    Schema for global MadCap output configuration, loaded from
    type = "config_output_plugin" or in the category configuration meta
    '''
    gim: Optional[Dict[str, str]] = Field(
        None, description='Optional metadata for GIM categories'
    )

    field_schema: Optional[dict[str, str]] = Field(
        None, description='Optional metadata for field schema entities'
    )

    config_output_plugin: Optional[Dict[str, str]] = Field(
        None, description='Optional metadata for schema categories'
    )
