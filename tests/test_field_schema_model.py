import pytest
from pydantic import ValidationError
from build_sdm.gim_schema.field_schema_model import (
    ConfigDocument,
    ConfigExtendDocumentation,
    FieldSchemaEntity,
    FieldSchemaField,
    SectionDefinition,
    SectionType
)


def test_field_schema_entity_allows_reserved_entity_type():
    """FieldSchemaEntity accepts entity_type="reserved"."""
    entity = FieldSchemaEntity(
        description='Reserved fields',
        entity_type='reserved',
        fields=[
            FieldSchemaField(
                field_suffix='timestamp',
                field_type='date',
                description='Event timestamp'
            )
        ]
    )
    assert entity.entity_type == 'reserved'


def test_field_schema_entity_rejects_invalid_entity_type():
    """FieldSchemaEntity rejects an entity_type outside the allowed literal values."""
    with pytest.raises(ValidationError):
        FieldSchemaEntity(
            description='Invalid entity',
            entity_type='bogus',
            fields=[]
        )


def test_field_schema_entity_sub_type_requires_applies_to():
    """FieldSchemaEntity requires a non-empty applies_to when entity_type="sub"."""
    with pytest.raises(ValidationError) as excinfo:
        FieldSchemaEntity(
            description='Hash sub-fields',
            entity_type='sub',
            fields=[]
        )
    assert 'applies_to must be a non-empty list' in str(excinfo.value)


def test_field_schema_entity_sub_type_accepts_applies_to():
    """FieldSchemaEntity accepts a populated applies_to when entity_type="sub"."""
    entity = FieldSchemaEntity(
        description='Hash sub-fields',
        entity_type='sub',
        fields=[],
        applies_to=['file', 'process']
    )
    assert entity.applies_to == ['file', 'process']


def test_field_schema_entity_top_type_rejects_applies_to():
    """FieldSchemaEntity rejects applies_to when entity_type is not "sub"."""
    with pytest.raises(ValidationError) as excinfo:
        FieldSchemaEntity(
            description='File fields',
            entity_type='top',
            fields=[],
            applies_to=['file']
        )
    assert 'applies_to is only allowed when entity_type is "sub"' in str(excinfo.value)


def test_valid_paragraph_section():
    doc = ConfigExtendDocumentation(
        sections=[
            SectionDefinition(
                type=SectionType.PARAGRAPHS,
                section_header="Intro",
                content=["Line 1", "Line 2"]
            )
        ]
    )
    assert len(doc.sections) == 1
    assert doc.sections[0].type == SectionType.PARAGRAPHS

def test_valid_hint_section():
    doc = ConfigExtendDocumentation(
        sections=[
            SectionDefinition(
                type=SectionType.HINT,
                content="This is a helpful tip."
            )
        ]
    )
    assert doc.sections[0].content.startswith("This is")

def test_invalid_paragraphs_with_string_content():
    with pytest.raises(ValidationError) as excinfo:
        ConfigExtendDocumentation(
            sections=[
                SectionDefinition(
                    type=SectionType.PARAGRAPHS,
                    content="This should be a list, not a string"
                )
            ]
        )
    assert "must be a list of strings" in str(excinfo.value)

def test_invalid_hint_with_list_content():
    with pytest.raises(ValidationError) as excinfo:
        ConfigExtendDocumentation(
            sections=[
                SectionDefinition(
                    type=SectionType.HINT,
                    content=["Not", "a", "single", "string"]
                )
            ]
        )
    assert "must be a string" in str(excinfo.value)

def test_list_ordered_with_valid_content():
    doc = ConfigExtendDocumentation(
        sections=[
            SectionDefinition(
                type=SectionType.LIST_ORDERED,
                section_header="Steps",
                content=["First", "Second", "Third"]
            )
        ]
    )
    assert isinstance(doc.sections[0].content, list)

def test_table_with_invalid_mixed_type_content():
    with pytest.raises(ValidationError) as excinfo:
        ConfigExtendDocumentation(
            sections=[
                SectionDefinition(
                    type=SectionType.TABLE,
                    content=["Row 1", 42, "Row 3"]
                )
            ]
        )
    assert "must be a list of strings" in str(excinfo.value)

def test_config_document_accepts_sdm_version_registry():
    """ConfigDocument accepts a dedicated sdm_version block alongside the existing config fields."""
    doc = ConfigDocument(
        type='config',
        sdm_version={'current_version': '7.1.0'}
    )
    assert doc.sdm_version == {'current_version': '7.1.0'}

def test_config_document_sdm_version_defaults_to_none():
    """ConfigDocument's sdm_version is optional and defaults to None."""
    doc = ConfigDocument(type='config')
    assert doc.sdm_version is None
