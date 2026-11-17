import logging
import pytest
from output_plugins.madcap_html_output import MadcapHtmlOutput


@pytest.fixture
def plugin():
    return MadcapHtmlOutput()


def test_build_schema_table_lines_basic(plugin):
    """
    Test that valid schema fields are correctly transformed into table rows.
    """
    entity_name = 'alert'
    entity_data = [
        {
            'field_suffix': 'indicator',
            'field_type': 'keyword',
            'description': 'Primary indicator value',
            'example_values': ['hash123', 'domain.com']
        },
        {
            'field_suffix': 'confidence',
            'field_type': 'integer',
            'description': 'Confidence score',
            'example_values': [80, 90]
        }
    ]

    expected = [
        {
            'field': 'alert_confidence',
            'field_type': 'integer',
            'description': 'Confidence score',
            'example_values': [80, 90]
        },
        {
            'field': 'alert_indicator',
            'field_type': 'keyword',
            'description': 'Primary indicator value',
            'example_values': ['hash123', 'domain.com']
        }
    ]

    result = plugin._build_schema_table_lines(entity_name, 'top', entity_data)
    assert result == expected


def test_missing_field_suffix_skipped(plugin, caplog):
    """
    Ensure entries without a field_suffix are skipped and a warning is logged.
    """
    entity_name = 'threat'
    entity_data = [
        {
            # Missing field_suffix
            'field_type': 'text',
            'description': 'Some desc',
            'example_values': ['abc']
        },
        {
            'field_suffix': 'source',
            'field_type': 'keyword',
            'description': 'Threat source',
            'example_values': ['malware.exe']
        }
    ]

    caplog.set_level(logging.WARNING, logger=plugin.logger.name)

    result = plugin._build_schema_table_lines(entity_name, 'top', entity_data)

    assert len(result) == 1
    assert result[0]['field'] == 'threat_source'

    warnings = [rec for rec in caplog.records if rec.levelname == 'WARNING']
    assert any('missing field_suffix:' in rec.getMessage().lower() for rec in warnings)


def test_unexpected_entry_shape_skipped(plugin, caplog):
    """
    Ensure completely invalid or malformed entries don't crash the method.
    """
    entity_name = 'asset'
    entity_data = [
        'this is not a dict',
        123,
        None,
        {
            'field_suffix': 'hostname',
            'field_type': 'keyword',
            'description': 'Host name',
            'example_values': ['srv01']
        }
    ]

    caplog.set_level(logging.WARNING, logger=plugin.logger.name)

    result = plugin._build_schema_table_lines(entity_name, 'top', entity_data)

    # Only the valid one should be returned
    assert len(result) == 1
    assert result[0]['field'] == 'asset_hostname'

    # Ensure at least one warning was logged
    warnings = [rec for rec in caplog.records if rec.levelname == 'WARNING']
    assert any('Skipping invalid schema line ' in rec.getMessage() for rec in warnings)


def test_build_schema_table_lines_reserved_no_prefix(plugin):
    """
    Ensure entity_type="reserved" fields use field_suffix as the literal field
    name, without prefixing it with the entity name.
    """
    entity_name = 'reserved'
    entity_data = [
        {
            'field_suffix': 'timestamp',
            'field_type': 'date',
            'description': 'Event timestamp',
            'example_values': ['2026-07-28T14:32:10.123Z']
        },
        {
            'field_suffix': 'sdm_version',
            'field_type': 'keyword',
            'description': 'SDM schema version',
            'example_values': ['7.1.0']
        }
    ]

    result = plugin._build_schema_table_lines(entity_name, 'reserved', entity_data)

    assert [row['field'] for row in result] == ['sdm_version', 'timestamp']


def test_build_schema_table_lines_sorts_alphabetically(plugin):
    """
    Ensure table rows are returned sorted alphabetically by field name,
    regardless of the order fields appear in the source data.
    """
    entity_name = 'sample'
    entity_data = [
        {
            'field_suffix': 'zebra',
            'field_type': 'keyword',
            'description': 'Zebra field',
            'example_values': ['z']
        },
        {
            'field_suffix': 'apple',
            'field_type': 'keyword',
            'description': 'Apple field',
            'example_values': ['a']
        },
        {
            'field_suffix': 'mango',
            'field_type': 'keyword',
            'description': 'Mango field',
            'example_values': ['m']
        }
    ]

    result = plugin._build_schema_table_lines(entity_name, 'top', entity_data)

    assert [row['field'] for row in result] == ['sample_apple', 'sample_mango', 'sample_zebra']
