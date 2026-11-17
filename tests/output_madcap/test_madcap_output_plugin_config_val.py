import logging
from pathlib import Path
from sys import path
from build_sdm.output_plugins.madcap_html_output import (
    TopLevelGimSectionMetadata,
    TopLevelFieldSchemaSectionMetadata,
)
from build_sdm.output_plugins.madcap_html_output import MadcapHtmlOutput
from build_sdm.output_plugins.madcap_html_output import MadcapHtmlOutputPluginConfig

def test_validate_category_plugin_config_valid():
    '''
    Should validate and return a config object when given correct string values.

    This confirms that a proper category-level plugin config dictionary with
    valid types (i.e., a string template filename) passes validation and is
    parsed correctly into a Pydantic model.
    '''
    plugin = MadcapHtmlOutput()
    plugin.logger.setLevel(logging.CRITICAL)

    raw_config = {'category_template_filename': 'custom_template.j2'}
    result = plugin._validate_category_plugin_config(raw_config, 'network')

    assert isinstance(result, MadcapHtmlOutputPluginConfig)
    assert result.category_template_filename == 'custom_template.j2'


def test_validate_category_plugin_config_empty_uses_default():
    '''
    Should return a config object using default template when no config is supplied.

    This ensures that when no values are provided in the config, the Pydantic
    schema uses its default for `category_template_filename`, verifying fallback logic.
    '''
    plugin = MadcapHtmlOutput()
    plugin.logger.setLevel(logging.CRITICAL)

    result = plugin._validate_category_plugin_config({}, 'network')

    assert isinstance(result, MadcapHtmlOutputPluginConfig)
    assert result.category_template_filename == 'gim_category_template.j2'  # default


def test_validate_category_plugin_config_coercion_behavior():
    '''
    Should reject non-string values when StrictStr is used for template filenames.

    This verifies that the schema now uses strict typing (StrictStr), and that
    values like integers are *not* coerced into strings. The plugin should log
    an error and return None when invalid types are encountered.
    '''
    plugin = MadcapHtmlOutput()
    raw_config = {'category_template_filename': 123}

    result = plugin._validate_category_plugin_config(raw_config, 'network')

    assert result is None


def test_gim_top_level_config_valid():
    '''
    Should parse a valid GIM section config correctly.

    Verifies that the GIM section top-level metadata structure is accepted
    and all expected fields are populated correctly.
    '''
    data = {
        'title': 'Test GIM Title',
        'intro': 'Test GIM Intro',
        'template': 'custom_gim_template.j2'
    }
    config = TopLevelGimSectionMetadata(**data)
    assert config.title == 'Test GIM Title'
    assert config.template == 'custom_gim_template.j2'


def test_gim_top_level_config_default_template():
    '''
    Should use default template when GIM top-level config omits the template key.

    Verifies that the Pydantic model provides a default template name when none
    is explicitly defined in the GIM section.
    '''
    data = {
        'title': 'Test Title',
        'intro': 'Test Intro'
        # no template provided
    }
    config = TopLevelGimSectionMetadata(**data)
    assert config.template == 'gim_category_top_template.j2'


def test_field_schema_top_level_config_valid():
    '''
    Should correctly initialize a field schema section with all values present.

    Ensures that all explicitly defined top-level metadata fields for field schema
    documentation are preserved and parsed.
    '''
    data = {
        'title': 'Field Schema Title',
        'intro': 'Intro about field schema',
        'template': 'custom_field_schema_template.j2'
    }
    config = TopLevelFieldSchemaSectionMetadata(**data)
    assert config.template == 'custom_field_schema_template.j2'


def test_field_schema_top_level_config_default_template():
    '''
    Should apply default template name when not provided in field schema config.

    This verifies that even if the field schema top-level config is incomplete
    (e.g., missing a template key), the Pydantic schema provides a fallback.
    '''
    data = {
        'title': 'Fallback',
        'intro': 'Should default template'
    }
    config = TopLevelFieldSchemaSectionMetadata(**data)
    assert config.template == 'field_schema_top_template.j2'
