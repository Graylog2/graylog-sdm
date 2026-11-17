import pytest
from pathlib import Path
from pydantic import ValidationError
from build_sdm.config_loader import _process_field_schema_file
from build_sdm.gim_schema.field_schema_model import FieldSchemaDocument

def test_valid_field_schema_parsing():
    """
    Validates that a well-formed field_schema TOML structure can be parsed into the Pydantic model.
    """
    toml_data = {
        'type': 'field_schema',
        'alert': {
            'description': 'Test description',
            'entity_type': 'top',
            'fields': [
                {
                    'field_suffix': 'category',
                    'example_values': 'foo, bar',
                    'field_type': 'keyword',
                    'description': 'Some text'
                }
            ]
        }
    }

    doc = FieldSchemaDocument.parse_obj(toml_data)
    assert doc.type == 'field_schema'
    assert 'alert' in doc.entities
    assert doc.entities['alert'].fields[0].field_type == 'keyword'


def test_invalid_field_type_raises():
    """
    Verifies that a field with an invalid field_type causes validation to fail.
    """
    bad_toml_data = {
        'type': 'field_schema',
        'alert': {
            'description': 'Test description',
            'entity_type': 'top',
            'fields': [
                {
                    'field_suffix': 'category',
                    'example_values': 'bad',
                    'field_type': 'INVALID_TYPE',
                    'description': 'Some description'
                }
            ]
        }
    }

    with pytest.raises(ValidationError) as excinfo:
        FieldSchemaDocument.parse_obj(bad_toml_data)

    errors = excinfo.value.errors()
    assert len(errors) == 1
    assert errors[0]['loc'] == ('entities', 'alert', 'fields', 0, 'field_type')
    assert 'Invalid field_type:' in errors[0]['msg']


def test_missing_required_field_raises():
    """
    Verifies that missing a required field in the field definition raises validation error.
    """
    missing_data = {
        'type': 'field_schema',
        'alert': {
            'description': 'Test',
            'entity_type': 'top',
            'fields': [
                {
                    'field_suffix': 'missing_description',
                    'field_type': 'keyword'
                    # 'description' missing
                }
            ]
        }
    }

    with pytest.raises(ValidationError) as excinfo:
        FieldSchemaDocument.parse_obj(missing_data)
    assert 'description' in str(excinfo.value)


def test_empty_fields_list_valid():
    """
    A field_schema entity with no fields defined should still be valid.
    """
    data = {
        'type': 'field_schema',
        'alert': {
            'description': 'No fields yet',
            'entity_type': 'top',
            'fields': []
        }
    }

    doc = FieldSchemaDocument.parse_obj(data)
    assert doc.entities['alert'].fields == []

def test_field_schema_valid_single_entity(tmp_path):
    file = tmp_path / 'valid_field_schema.toml'
    file.write_text('''
        type = "field_schema"

        [alert]
        description = "Test description"
        entity_type = "top"

        [[alert.fields]]
        field_suffix = "name"
        field_type = "keyword"
        description = "Name field"
    ''', encoding='utf-8')

    parsed = _process_field_schema_file(file, {
        'type': 'field_schema',
        'alert': {
            'description': 'Test description',
            'entity_type': 'top',
            'fields': [
                {
                    'field_suffix': 'name',
                    'field_type': 'keyword',
                    'description': 'Name field'
                }
            ]
        }
    })

    assert parsed['type'] == 'field_schema'
    assert 'alert' in parsed

    entity = parsed['alert']
    assert entity.entity_type == 'top'
    assert entity.description == 'Test description'
    assert isinstance(entity.fields, list)
    assert len(entity.fields) == 1

    field = entity.fields[0]
    assert field.field_suffix == 'name'
    assert field.field_type == 'keyword'
    assert field.description == 'Name field'


def test_field_schema_invalid_field_type():
    invalid_data = {
        'type': 'field_schema',
        'alert': {
            'description': 'Invalid',
            'entity_type': 'top',
            'fields': [
                {
                    'field_suffix': 'bad',
                    'field_type': 'not_a_valid_type',
                    'description': 'Should fail'
                }
            ]
        }
    }

    with pytest.raises(ValidationError) as excinfo:
        FieldSchemaDocument.parse_obj(invalid_data)

    assert "field_type" in str(excinfo.value)


def test_field_schema_missing_required_field():
    missing_field = {
        'type': 'field_schema',
        'alert': {
            'entity_type': 'top',
            'fields': [
                {
                    'field_suffix': 'x',
                    'field_type': 'keyword'
                    # missing description
                }
            ]
        }
    }

    with pytest.raises(ValidationError) as excinfo:
        FieldSchemaDocument.parse_obj(missing_field)

    assert "description" in str(excinfo.value)
